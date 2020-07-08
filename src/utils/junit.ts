import { getProps, sortBy, withSentry, AssertionError } from '@/utils';
import decodeBuffer from '@/utils/decode';

function mapHTMLCollection<T>(
    collection: HTMLCollection,
    mapper: (node: Element, index: number) => T,
): T[] {
    return Array.from(collection, mapper);
}

function getAttribute<Y extends string | number>(
    node: Element,
    name: string,
    dflt: Y | null = null,
): string | Y {
    const attr = node.getAttribute(name);
    if (dflt == null) {
        AssertionError.assert(attr != null, `Attribute ${name} not found in ${node.outerHTML}`);
        return attr;
    } else {
        return attr ?? dflt;
    }
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
    public readonly content: string[] | null;

    constructor(
        content: string | null,
        public readonly message: string | null,
        public readonly state: CGJunitCaseState,
        public readonly name: string,
        public readonly classname: string,
        public readonly time: number,
    ) {
        this.content = content ? content.split('\n') : null;
        Object.freeze(this);
    }

    static fromXml(node: Element) {
        const firstChild = node.firstElementChild;

        let contentType: CGJunitCaseState;
        const maybeContentType = firstChild?.tagName;

        if (isValidState(maybeContentType)) {
            contentType = maybeContentType;
        } else if (maybeContentType == null) {
            contentType = 'success';
        } else {
            contentType = 'unknown';
        }
        const content: string | null = firstChild ? firstChild.textContent : null;
        const message = firstChild ? firstChild.getAttribute('message') : null;

        return new CGJunitCase(
            content,
            message,
            contentType,
            getAttribute(node, 'name'),
            getAttribute(node, 'classname'),
            parseFloat(getAttribute(node, 'time')),
        );
    }

    get fontAwesomeIcon() {
        return fontAwesomeIconMap[this.state];
    }
}

class CGJunitSuite {
    successful: number;

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
        this.successful = this.filterCases('success').length;
        this.runTests = tests - skipped;
        this.totalTests = tests;

        AssertionError.assert(
            errors === this.filterCases('error').length,
            'Amount of errors does not match the found "errors" attribute',
        );
        AssertionError.assert(
            failures === this.filterCases('failure').length,
            'Amount of failures does not match the found "failures" attribute',
        );
        AssertionError.assert(
            skipped === this.filterCases('skipped').length,
            'Amount of skipped cases does not match the found "skipped" attribute',
        );

        Object.freeze(this.cases);
        Object.freeze(this);
    }

    private filterCases(state: CGJunitCaseState): CGJunitCase[] {
        return this.cases.filter(c => c.state === state);
    }

    static fromXml(node: Element) {
        const suiteName: string = getAttribute(node, 'name');

        return new CGJunitSuite(
            mapHTMLCollection(node.children, CGJunitCase.fromXml),
            suiteName,
            parseInt(getAttribute(node, 'errors'), 10),
            parseInt(getAttribute(node, 'failures'), 10),
            parseInt(getAttribute(node, 'skipped', '0'), 10),
            parseInt(getAttribute(node, 'tests'), 10),
        );
    }
}

export class CGJunit {
    suites: ReadonlyArray<CGJunitSuite>;

    constructor(public id: string, suites: CGJunitSuite[]) {
        this.suites = sortBy(suites, x => [x.failures <= 0]);

        Object.freeze(this.suites);
        Object.freeze(this);
    }

    static fromXml(id: string, xml: string): CGJunit {
        const rootNodes = CGJunit.parseXML(xml);

        return new CGJunit(id, mapHTMLCollection(rootNodes, CGJunitSuite.fromXml));
    }

    private static parseXML(xml: string): HTMLCollection {
        const xmlDoc = new DOMParser().parseFromString(decodeBuffer(xml), 'text/xml');

        CGJunit.maybeRaiseParserError(xmlDoc);

        let rootNodes = xmlDoc.children;
        if (rootNodes.length === 1 && rootNodes[0].tagName === 'testsuites') {
            rootNodes = rootNodes[0].children;
        }

        return rootNodes;
    }

    private static maybeRaiseParserError(xmlDoc: Document): void {
        // The <parsererror> element might be nested in some other elements, so
        // use querySelector to find it.
        const perr = xmlDoc.querySelector('parsererror');

        if (perr != null) {
            withSentry(Sentry => {
                Sentry.captureMessage('Could not parse as XML');
            });
            throw new Error(getProps(perr, undefined, 'textContent'));
        }
    }
}
