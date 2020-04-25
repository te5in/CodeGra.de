import { Document, getBackend } from '@/utils/Document';

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

export class PlagiarismDocument {
    private doc: Document;

    constructor(backend: string) {
        this.doc = getBackend(backend);
    }

    render(matches: any, opts: PlagiarismOptions) {
        console.log(this, matches, opts);
    }
}
