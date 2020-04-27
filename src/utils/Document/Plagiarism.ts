import {
    CodeBlock,
    Highlight,
    ColumnLayout,
    DocumentRoot,
    backends,
    NewPage,
    render,
} from '@/utils/Document';
import { flatMap1, AssertionError } from '../typed';

export interface PlagiarismOptions {
    // The number of context lines to render before/after each match. Ignored
    // if entireFiles is set.
    contextLines?: number;

    // Render matches side by side or below each other.
    matchesAlign: 'newpage' | 'sidebyside' | 'sequential';

    // Render all files with matches in their entirety. Matches may not be
    // aligned as nicely in this mode.
    entireFiles?: boolean;
}

interface FileMatch {
    startLine: number;

    endLine: number;

    lines: string[];

    name: string;
}

export interface PlagMatch {
    matchA: FileMatch;

    matchB: FileMatch;

    color: [number, number, number];
}

function makeCodeBlock(match: PlagMatch, context: number): [CodeBlock, CodeBlock] {
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
    const highlight = new Highlight(background, textColor);

    function maker(innerMatch: FileMatch) {
        return {
            firstLine: Math.max(innerMatch.startLine - context + 1, 1),
            lines: innerMatch.lines.slice(
                Math.max(innerMatch.startLine - context, 0),
                innerMatch.endLine + context,
            ),
            caption: `File ${innerMatch.name} of `,
            highlights: [
                {
                    start: innerMatch.startLine + 1,
                    end: innerMatch.endLine,
                    highlight,
                },
            ],
        };
    }

    return [maker(match.matchA), maker(match.matchB)];
}

export class PlagiarismDocument {
    constructor(private readonly backend: keyof typeof backends) {}

    render(matches: PlagMatch[], opts: PlagiarismOptions): Promise<Buffer> {
        const context = opts.contextLines ?? 0;
        const blocks = flatMap1(matches, (match): (
            | ColumnLayout<CodeBlock>
            | NewPage
            | CodeBlock
        )[] => {
            const [b1, b2] = makeCodeBlock(match, context);
            switch (opts.matchesAlign) {
                case 'sidebyside':
                    return [new ColumnLayout([b1, b2])];
                case 'sequential':
                    return [b1, b2];
                case 'newpage':
                    return [b1, new NewPage(), b2, new NewPage()];
                default:
                    return AssertionError.assert(false, 'unknown matches align found');
            }
        });
        const root = DocumentRoot.makeEmpty().addChildren(blocks);

        return render(this.backend, root);
    }
}
