import {
    CodeBlock,
    Highlight,
    ColumnLayout,
    ContentBlock,
    MonospaceContent,
    NonBreakingContent,
    Section,
    SubSection,
    DocumentNode,
    DocumentRoot,
    backends,
    NewPage,
    render,
} from '@/utils/Document';
import { User } from '@/models';
import { flatMap1, AssertionError } from '../typed';

export interface PlagiarismOptions {
    // The number of context lines to render before/after each match. Ignored
    // if entireFiles is set.
    contextLines: number;

    // Render matches side by side or below each other.
    matchesAlign: 'sidebyside' | 'sequential';

    // Render each match on a new page.
    newPage: boolean;

    // Render all files with matches in their entirety. Matches may not be
    // aligned as nicely in this mode.
    entireFiles: boolean;
}

interface FileMatch {
    startLine: number;

    endLine: number;

    lines: string[];

    name: string;

    user: User;
}

export interface PlagMatch {
    matchA: FileMatch;

    matchB: FileMatch;

    color: [number, number, number];
}

function bgColor(colorElement: number) {
    return Math.round(Math.min(255, colorElement * 0.2 + 0.8 * 255));
}

function fgColor(colorElement: number) {
    return Math.round(colorElement / 2);
}

function makeCodeBlock(match: PlagMatch, opts: PlagiarismOptions): [CodeBlock, CodeBlock] {
    const background = {
        red: bgColor(match.color[0]),
        green: bgColor(match.color[1]),
        blue: bgColor(match.color[2]),
    };
    const textColor = {
        red: fgColor(match.color[0]),
        green: fgColor(match.color[1]),
        blue: fgColor(match.color[2]),
    };
    const highlight = new Highlight(background, textColor);
    const context = opts.contextLines ?? 0;

    function maker(innerMatch: FileMatch) {
        return {
            firstLine: Math.max(innerMatch.startLine - context + 1, 1),
            lines: innerMatch.lines.slice(
                Math.max(innerMatch.startLine - context, 0),
                innerMatch.endLine + context,
            ),
            caption: new ContentBlock([
                'File ',
                new MonospaceContent(new ContentBlock([innerMatch.name])),
                ' of ',
                new NonBreakingContent([innerMatch.user.name]),
            ]),
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

function makeSection(match: PlagMatch, idx: number, opts: PlagiarismOptions): SubSection {
    const [b1, b2] = makeCodeBlock(match, opts);

    let children: DocumentNode[];
    switch (opts.matchesAlign) {
        case 'sidebyside':
            children = [new ColumnLayout([b1, b2])];
            break;
        case 'sequential':
            children = [b1, b2];
            break;
        default:
            return AssertionError.assert(false, 'unknown matches align found');
    }

    if (opts.newPage) {
        children = flatMap1(children, c => [c, new NewPage()]);
    }

    // TODO: Use actual match index.
    // TODO: Discuss if we want to change this section header.
    return new SubSection(`Match ${idx + 1}`, children);
}

export class PlagiarismDocument {
    constructor(private readonly backend: keyof typeof backends) {}

    render(matches: PlagMatch[], opts: PlagiarismOptions): Promise<Buffer> {
        const blocks = matches.map((match, i): Section => makeSection(match, i, opts));
        const section = new Section('Plagiarism matches', blocks);
        const root = DocumentRoot.makeEmpty().addChildren([section]);

        return render(this.backend, root);
    }
}
