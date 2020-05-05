// SPDX-License-Identifier: AGPL-3.0-only
import { getProps, highlightCode } from '@/utils/typed';

function maybeJoinText(txt: string | string[]): string {
    if (Array.isArray(txt)) {
        return txt.join('');
    }
    return txt;
}

/* eslint-disable camelcase */
interface IPythonBaseCell {
    cell_type?: string;
    source?: string | string[];
    input?: string | string[];
}

interface IPythonRawCell extends IPythonBaseCell {
    cell_type: 'raw';
}

interface IPythonCodeCell extends IPythonBaseCell {
    cell_type: 'code';
    source: string | string[];
    outputs: (
        | {
              output_type?: Exclude<'stream', string>;
          }
        | {
              output_type: 'stream';
              text: string | string[];
          }
    )[];
}

interface IPythonGenericCell extends IPythonBaseCell {
    cell_type?: Exclude<'raw' | 'code', string>;
}

type IPythonDataCell = IPythonGenericCell | IPythonRawCell | IPythonCodeCell;

interface CGIPythonBaseDataCell extends IPythonBaseCell {
    feedback_offset: number;
}

interface CGIPythonCodeCell extends CGIPythonBaseDataCell {
    cell_type?: string;
    outputs?: ReadonlyArray<CGIPythonCodeCellOutput>;
    source: string[];
}

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

interface CGIPythonGenericCell extends CGIPythonBaseDataCell {
    cell_type?: Exclude<'raw' | 'code', string>;
    source: string;
}

type CGIPythonDataCell = CGIPythonGenericCell | CGIPythonCodeCell;

interface IPythonData {
    metadata?: {
        language_info?: {
            name?: string;
        };
    };
    cells?: ReadonlyArray<IPythonDataCell>;
    worksheets?: ReadonlyArray<{
        cells?: ReadonlyArray<IPythonDataCell>;
    }>;
}
/* eslint-enable camelcase */

export function sourceLanguage(ipythonData: IPythonData) {
    return getProps(ipythonData, 'python', 'metadata', 'language_info', 'name');
}

export function getOutputCells(
    ipythonData: IPythonData,
    // eslint-disable-next-line
    highlight = (source: string[], lang: string, curOffset: number) => highlightCode(source, lang),
    processOther = <T extends CGIPythonDataCell | CGIPythonCodeCellOutput>(cell: T) => cell,
): ReadonlyArray<Readonly<CGIPythonDataCell>> {
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

        if (cell.cell_type === 'code') {
            const splitted = maybeJoinText(cell.source).split('\n');
            const initialOffset = curOffset;
            curOffset += splitted.length;

            const codeCell: CGIPythonCodeCell = {
                ...cell,
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
                ...cell,
                source: maybeJoinText(cell.source || cell.input || ''),
                feedback_offset: curOffset,
            };
            res.push(processOther(genericCell));
            curOffset += 1;
        }

        return res;
    }, []);
}
