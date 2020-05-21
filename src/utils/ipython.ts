// SPDX-License-Identifier: AGPL-3.0-only
import { OneOrOther, filterObject, getProps, highlightCode } from '@/utils/typed';

function maybeJoinText(txt: string | string[]): string {
    if (Array.isArray(txt)) {
        return txt.join('');
    }
    return txt;
}

/* eslint-disable camelcase */
type CellSource = string | string[];

type AnySource = OneOrOther<{ input: CellSource }, { source: CellSource }>;

type IPythonBaseCell = AnySource & {
    cell_type?: string;
};

type IPythonRawCell = IPythonBaseCell & {
    cell_type: 'raw';
};

type IPythonCodeCell = IPythonBaseCell & {
    cell_type: 'code';
    outputs: (
        | {
              output_type?: Exclude<'stream', string>;
          }
        | {
              output_type: 'stream';
              text: string | string[];
          }
    )[];
};

type IPythonGenericCell = IPythonBaseCell & {
    cell_type?: Exclude<'raw' | 'code', string>;
};

type IPythonDataCell = IPythonGenericCell | IPythonRawCell | IPythonCodeCell;

type CGIPythonBaseDataCell = IPythonBaseCell & {
    feedback_offset: number;
};

type CGIPythonCodeCell = CGIPythonBaseDataCell & {
    cell_type?: string;
    outputs?: ReadonlyArray<CGIPythonCodeCellOutput>;
    source: string[];
};

type CGIPythonCodeCellOutput =
    | {
          output_type?: Exclude<'stream', string>;
          feedback_offset: number;
      }
    | {
          feedback_offset: number;
          output_type: 'stream';
          text: string;
      };

type CGIPythonGenericCell = CGIPythonBaseDataCell & {
    cell_type?: Exclude<'raw' | 'code', string>;
    source: string;
};

type CGIPythonDataCell = CGIPythonGenericCell | CGIPythonCodeCell;

interface IPythonData {
    metadata?: {
        language_info?: {
            name?: string;
        };
    };
    nbformat?: number;
    cells?: ReadonlyArray<IPythonDataCell>;
    worksheets?: ReadonlyArray<{
        cells?: ReadonlyArray<IPythonDataCell>;
    }>;
}
/* eslint-enable camelcase */

export function sourceLanguage(ipythonData: IPythonData) {
    return getProps(ipythonData, 'python', 'metadata', 'language_info', 'name');
}

export function nbformatVersion(ipythonData: IPythonData): number {
    return getProps(ipythonData, 0, 'nbformat');
}

export function getOutputCells(
    ipythonData: IPythonData,
    // eslint-disable-next-line
    highlight = (source: string[], lang: string, curOffset: number) => highlightCode(source, lang),
    processOther = <T extends CGIPythonDataCell | CGIPythonCodeCellOutput>(cell: T) => cell,
): ReadonlyArray<Readonly<CGIPythonDataCell>> {
    if (nbformatVersion(ipythonData) < 3) {
        throw new RangeError('Only Jupyter Notebook format v3 or greater is supported.');
    }

    let curOffset = 0;
    const language = sourceLanguage(ipythonData);
    let cells = ipythonData.cells;
    if (!cells && ipythonData.worksheets != null) {
        cells = ipythonData.worksheets.reduce(
            (accum: IPythonDataCell[], sheet) => accum.concat(sheet?.cells ?? []),
            [],
        );
    }

    return (cells || []).reduce((res: CGIPythonDataCell[], cell) => {
        if (cell.cell_type === 'raw') {
            return res;
        }

        const props = filterObject(cell, (_, k) => k !== 'input');

        if (cell.cell_type === 'code') {
            const source = cell.source ?? cell.input;
            const splitted = maybeJoinText(source).split('\n');
            const initialOffset = curOffset;
            curOffset += splitted.length;

            const codeCell: CGIPythonCodeCell = {
                ...props,
                feedback_offset: initialOffset,
                source: highlight(splitted, language, initialOffset),
                outputs: cell.outputs.map(out => {
                    let newOut: CGIPythonCodeCellOutput;
                    if (out.output_type === 'stream') {
                        newOut = {
                            ...out,
                            text: maybeJoinText(out.text),
                            feedback_offset: curOffset,
                        };
                    } else {
                        newOut = {
                            ...out,
                            feedback_offset: curOffset,
                        };
                    }
                    curOffset += 1;
                    return processOther(newOut);
                }),
            };

            res.push(codeCell);
        } else {
            const genericCell: CGIPythonGenericCell = {
                ...props,
                source: maybeJoinText(cell.source || cell.input || ''),
                feedback_offset: curOffset,
            };
            res.push(processOther(genericCell));
            curOffset += 1;
        }

        return res;
    }, []);
}
