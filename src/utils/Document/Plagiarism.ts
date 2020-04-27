import {
    CodeBlock,
    Highlight,
    ColumnLayout,
    DocumentRoot,
    backends,
    render,
} from '@/utils/Document';
import { flatMap } from '../typed';

export interface PlagiarismOptions {
    // The number of context lines to render before/after each match. Ignored
    // if entireFiles is set.
    contextLines?: number;

    // Render matches side by side or below each other.
    sideBySide?: boolean;

    // Render all files with matches in their entirety. Matches may not be
    // aligned as nicely in this mode.
    entireFiles?: boolean;
}

export interface FileMatch {
    startLine: number;

    endLine: number;

    lines: string[];

    name: string;

    color: [number, number, number];
}

function makeCodeBlock(match: FileMatch, context: number): CodeBlock {
    const background = {
        red: Math.min(255, match.color[0] * 0.4 + 0.6 * 255),
        green: Math.min(255, match.color[1] * 0.4 + 0.6 * 255),
        blue: Math.min(255, match.color[2] * 0.4 + 0.6 * 255),
    };
    const textColor = {
        red: match.color[0] / 1.75,
        green: match.color[1] / 1.75,
        blue: match.color[2] / 1.75,
    };

    return {
        firstLine: Math.max(match.startLine - context + 1, 1),
        lines: match.lines.slice(Math.max(match.startLine - context, 0), match.endLine + context),
        caption: `File ${match.name} of `,
        highlights: [
            {
                start: match.startLine + 1,
                end: match.endLine,
                highlight: new Highlight(background, textColor),
            },
        ],
    };
}

export class PlagiarismDocument {
    constructor(private readonly backend: keyof typeof backends) {}

    render(matches: [FileMatch, FileMatch][], opts: PlagiarismOptions): Promise<Buffer> {
        const context = opts.contextLines ?? 0;
        const blocks = flatMap(matches, ([m1, m2]): (ColumnLayout<CodeBlock> | CodeBlock)[] => {
            console.log(m1, m2);
            const b1 = makeCodeBlock(m1, context);
            const b2 = makeCodeBlock(m2, context);
            if (opts.sideBySide) {
                return [new ColumnLayout([b1, b2])];
            }
            return [b1, b2];
        });
        const root = DocumentRoot.makeEmpty().addChildren(blocks);

        return render(this.backend, root);
    }
}
