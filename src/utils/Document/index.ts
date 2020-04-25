import { hasAttr, mapObject } from '@/utils';

export abstract class Document {
    static backendName: string;

    // Finalize the document and render it as a string.
    abstract render(): string;

    // Start a new section.
    abstract section(header: string): void;

    // Insert a paragraph. Multiple paragraphs should be separated by an empty
    // line.
    abstract paragraph(text: string): void;

    // Insert a code block.
    abstract code(code: CodeBlock): void;

    // Change the column layout.
    abstract columnLayout(nColumns: number): void;

    // Define a highlight that can be used to highlight specific lines in code
    // blocks.
    abstract defineHighlight(highlight: Highlight): HighlightID;

    defineHighlights(highlights: Highlight[]): HighlightID[] {
        return highlights.map(this.defineHighlight.bind(this));
    }
}

// Identifier that should uniquely identify a defined highlight.
type HighlightID = number;

interface CodeBlock {
    // Line number of the first line in the block.
    firstLine: number;

    // The lines of text to render.
    lines: string[];

    // Specification for lines to be highlighted.
    highlights: HighlightRange[];

    // Optional caption.
    caption?: string;
}

interface HighlightRange {
    start: number;
    end: number;
    highlightId: HighlightID;
}

interface Highlight {
    background: Color;
    foreground: Color;
}

interface Color {
    red: number;
    green: number;
    blue: number;
}

class LatexDocument extends Document {
    static backendName = 'LaTeX';

    private lines: string[] = [];

    private highlights: Highlight[] = [];

    render() {
        return `\\documentclass{article}
\\usepackage{listings}
\\usepackage{xcolor}

\\definecolor{bluekeywords}{rgb}{0.13, 0.13, 1}
\\definecolor{greencomments}{rgb}{0, 0.5, 0}
\\definecolor{redstrings}{rgb}{0.9, 0, 0}
\\definecolor{graynumbers}{rgb}{0.5, 0.5, 0.5}

${this._defineColors().join('\n')}

\\lstset{
    numbers=left,
    columns=fullflexible,
    showspaces=false,
    showtabs=false,
    breaklines=true,
    showstringspaces=false,
    breakatwhitespace=true,
    escapeinside={(*@}{@*)},
    commentstyle=\\color{greencomments},
    keywordstyle=\\color{bluekeywords},
    stringstyle=\\color{redstrings},
    numberstyle=\\color{graynumbers},
    basicstyle=\\ttfamily\\footnotesize,
    xleftmargin=12pt,
    rulesepcolor=\\color{graynumbers},
    tabsize=4,
    captionpos=b,
    frame=L
}

\\begin{document}

${this.lines.join('\n')}

\\end{document}`;
    }

    _defineColors(): string[] {
        return [].concat(
            ...this.highlights.map((highlight, id) => {
                const bg = highlight.background;
                const fg = highlight.foreground;
                return [
                    `\\definecolor{bg-color-${id}}{RGB}{${bg.red}, ${bg.green}, ${bg.blue}}`,
                    `\\definecolor{fg-color-${id}}{RGB}{${fg.red}, ${fg.green}, ${fg.blue}}`,
                ];
            }),
        );
    }

    section(header: string) {
        this.lines.push(`\\section{${header}}`);
    }

    paragraph(text: string) {
        this.lines.push(text, '\\\\');
    }

    code(code: CodeBlock) {
        // TODO: don't render caption when none given.
        this.lines.push(
            '\\begin{lstlisting}[',
            `    firstnumber=${code.firstLine},`,
            `    backgroundcolor=${this._makeHighlights(code.highlights)},`,
            `    caption={${code.caption}}]`,
            ...code.lines,
            '\\end{lstlisting}',
        );
    }

    _makeHighlights(ranges: HighlightRange[]): string {
        const sorted = ranges.sort((a, b) => a.end - b.end);
        return this._makeHighlightsSorted(sorted);
    }

    _makeHighlightsSorted(ranges: HighlightRange[]): string {
        // Ranges must be sorted and not overlap. Because there is no "and"
        // operator in TeX that is the only way we can guarantee that the
        // nested if-else below will work correctly.
        // TODO: Find a way to change the foreground color of specific lines.
        // Maybe simply wrapping each line in a {\color{fg-color-${id}} ...}
        // will work.

        const [cur, ...rest] = ranges;

        if (rest.length === 0) {
            return `
\\ifnum\\value{lstnumber}<${cur.end + 1}
    \\ifnum\\value{lstnumber}>${cur.start - 1}
        \\color{bg-color-${cur.highlightId}}
    \\fi
\\fi
            `.trim();
        } else {
            return `
\\ifnum\\value{lstnumber}<${cur.end + 1}
    \\ifnum\\value{lstnumber}>${cur.start - 1}
        \\color{bg-color-${cur.highlightId}}
    \\fi
\\else
    ${this._makeHighlightsSorted(rest)}
\\fi
            `.trim();
        }
    }

    defineHighlight(highlight: Highlight) {
        const id = this.highlights.length;
        this.highlights.push(highlight);
        return id;
    }

    columnLayout(nColumns: number) {
        // TODO
        console.log(this, nColumns);
    }
}

interface BackendMap {
    [key: string]: Document;
}

const backends: { [key: string]: Document } = {
    latex: LatexDocument,
};

export function getBackends(): string[] {
    return mapObject(backends, (backend: typeof Document) => backend.backendName);
}

export function getBackend(name: string): Document {
    if (!hasAttr(backends, name)) {
        throw new Error(`Invalid backend: ${name}`);
    }

    return new backends[name]();
}
