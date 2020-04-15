// SPDX-License-Identifier: AGPL-3.0-only
import { getProps, highlightCode } from '@/utils';

function maybeJoinText(txt) {
    if (Array.isArray(txt)) {
        return txt.join('');
    }
    return txt;
}

export function sourceLanguage(ipythonData) {
    return getProps(ipythonData, 'python', 'metadata', 'language_info', 'name');
}

export function getOutputCells(
    ipythonData,
    // eslint-disable-next-line
    highlight = (source, lang, curOffset) => highlightCode(source, lang),
    processOther = cell => cell,
) {
    let curOffset = 0;
    const language = sourceLanguage(ipythonData);
    let cells = ipythonData.cells;
    if (!cells && ipythonData.worksheets) {
        cells = ipythonData.worksheets.reduce((accum, sheet) => {
            accum.push(...sheet.cells);
            return accum;
        }, []);
    }

    return (cells || []).reduce((res, cell) => {
        if (cell.cell_type === 'raw') {
            return res;
        }

        cell.source = maybeJoinText(cell.source || cell.input);
        cell.feedback_offset = curOffset;

        if (cell.cell_type === 'code') {
            res.push(cell);
            const splitted = cell.source.split('\n');

            cell.source = highlight(splitted, language, curOffset);
            curOffset += splitted.length;
            cell.outputs = cell.outputs.map(out => {
                out.feedback_offset = curOffset;
                curOffset += 1;
                if (out.output_type === 'stream') {
                    out.text = maybeJoinText(out.text);
                }
                return processOther(out);
            });
        } else {
            res.push(processOther(cell));
            curOffset += 1;
        }
        return res;
    }, []);
}
