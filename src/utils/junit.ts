import { sortBy, withSentry, AssertionError } from '@/utils';
import decodeBuffer from '@/utils/decode';

function mapHTMLCollection<T>(
    collection: HTMLCollection,
    mapper: (node: Element, index: number) => T,
): T[] {
    const res = [];
    for (let i = 0, length = collection.length; i < length; ++i) {
        res.push(mapper(collection[i], i));
    }
    return res;
}

function getAttribute(node: Element, name: string): string {
    const attr = node.getAttribute(name);
    AssertionError.assert(attr != null, `Attribute ${name} not found in ${node.outerHTML}`);
    return attr;
}

const fontAwesomeIconMap = <const>{
    success: { icon: 'check', cls: 'text-success' },
    failure: { icon: 'times', cls: 'text-danger' },
    skipped: { icon: 'ban', cls: 'text-muted' },
    error: { icon: 'exclamation', cls: 'text-danger' },
    unknown: { icon: 'question', cls: 'text-danger' },
};

type CGJunitCaseState = keyof typeof fontAwesomeIconMap;

function isValidState(state: unknown): state is CGJunitCaseState {
    return typeof state === 'string' && state in fontAwesomeIconMap;
}

class CGJunitCase {
    public content: string[] | null;

    constructor(
        content: string | null,
        public readonly contentType: CGJunitCaseState,
        public readonly name: string,
        public readonly classname: string,
        public readonly time: number,
    ) {
        this.content = content ? content.split('\n') : null;
        Object.freeze(this);
    }

    static fromXml(node: Element) {
        const firstChild = node.firstElementChild;

        let contentType: CGJunitCaseState | null;
        const maybeContentType = firstChild?.tagName;

        if (isValidState(maybeContentType)) {
            contentType = maybeContentType;
        } else if (maybeContentType == null) {
            contentType = 'success';
        } else {
            contentType = 'unknown';
        }

        return new CGJunitCase(
            firstChild && firstChild.textContent,
            contentType,
            getAttribute(node, 'name'),
            getAttribute(node, 'classname'),
            parseFloat(getAttribute(node, 'time')),
        );
    }

    get state(): CGJunitCaseState {
        return this.contentType;
    }

    get fontAwesomeIcon() {
        return fontAwesomeIconMap[this.state];
    }
}

class CGJunitSuite {
    runTests: number;

    totalTests: number;

    constructor(
        public cases: CGJunitCase[],
        public name: string,
        public errors: number,
        public failures: number,
        public skipped: number,
        tests: number,
    ) {
        this.cases = cases;

        this.name = name;
        this.errors = errors;
        this.failures = failures;
        this.skipped = skipped;
        this.runTests = tests - skipped;
        this.totalTests = tests;

        Object.freeze(this.cases);
        Object.freeze(this);
    }

    get successful() {
        return this.runTests - (this.errors + this.failures);
    }

    static fromXml(node: Element) {
        const suiteName = getAttribute(node, 'name');

        return new CGJunitSuite(
            mapHTMLCollection(node.children, CGJunitCase.fromXml),
            suiteName,
            parseInt(getAttribute(node, 'errors'), 10),
            parseInt(getAttribute(node, 'failures'), 10),
            parseInt(getAttribute(node, 'skipped') ?? 0, 10),
            parseInt(getAttribute(node, 'tests'), 10),
        );
    }
}

export class CGJunit {
    suites: ReadonlyArray<CGJunitSuite>;

    constructor(suites: CGJunitSuite[]) {
        this.suites = sortBy(suites, x => [x.failures <= 0]);

        Object.freeze(this.suites);
        Object.freeze(this);
    }

    static fromXml(xml: string): CGJunit {
        const rootNodes = CGJunit.parseXML(xml);

        return new CGJunit(mapHTMLCollection(rootNodes, CGJunitSuite.fromXml));
    }

    private static parseXML(xml: string): HTMLCollection {
        const xmlDoc = new DOMParser().parseFromString(decodeBuffer(xml), 'text/xml');

        const parserError = CGJunit.getParserError(xmlDoc);
        if (parserError != null) {
            withSentry(Sentry => {
                Sentry.captureMessage(`Could not parse as XML: ${xmlDoc}`);
            });
            throw new Error(parserError);
        }

        let rootNodes = xmlDoc.children;
        if (rootNodes.length === 1 && rootNodes[0].tagName === 'testsuites') {
            rootNodes = rootNodes[0].children;
        }

        return rootNodes;
    }

    private static getParserError(xmlDoc: Document): string | null {
        const html = xmlDoc.firstElementChild;
        const body = html?.firstElementChild;
        const perr = body?.firstElementChild;

        if (perr && perr.tagName === 'parsererror') {
            return perr.textContent;
        } else {
            return null;
        }
    }
}
