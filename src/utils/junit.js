function mapHTMLCollection(collection, mapper) {
    const res = [];
    for (let i = 0, length = collection.length; i < length; ++i) {
        res.push(mapper(collection[i], i));
    }
    return res;
}

class CGJunitCase {
    constructor(content, contentType, name, classname, time) {
        this.content = content ? content.split('\n') : null;
        this.contentType = contentType;
        this.name = name;
        this.classname = classname;
        this.time = time;
        Object.freeze(this);
    }

    static fromXml(node) {
        const firstChild = node.firstElementChild;
        return new CGJunitCase(
            firstChild && firstChild.textContent,
            firstChild && firstChild.tagName,
            node.attributes.name.value,
            node.attributes.classname.value,
            parseFloat(node.attributes.time.value),
        );
    }

    get state() {
        return this.contentType || 'success';
    }

    get fontAwesomeIcon() {
        switch (this.state) {
            case 'success':
                return { icon: 'check', cls: 'text-success' };
            case 'failure':
                return { icon: 'times', cls: 'text-danger' };
            case 'error':
            default:
                return { icon: 'exclamation', cls: 'text-danger' };
        }
    }
}

class CGJunitSuite {
    constructor(cases, name, errors, failures, tests) {
        this.cases = cases;

        this.name = name;
        this.errors = errors;
        this.failures = failures;
        this.tests = tests;

        Object.freeze(this.cases);
        Object.freeze(this);
    }

    get successful() {
        return this.tests - (this.errors + this.failures);
    }

    static fromXml(node) {
        const attrs = node.attributes;
        const suiteName = attrs.name.value;

        return new CGJunitSuite(
            mapHTMLCollection(node.children, CGJunitCase.fromXml),
            suiteName,
            parseInt(attrs.errors.value, 10),
            parseInt(attrs.failures.value, 10),
            parseInt(attrs.tests.value, 10),
        );
    }
}
export class CGJunit {
    constructor(suites) {
        this.suites = suites;

        Object.freeze(this.suites);
        Object.freeze(this);
    }

    static fromXml(xmlDoc) {
        const rootNodes = xmlDoc.children;
        if (rootNodes.length === 1 && rootNodes[0].tagName === 'testsuites') {
            return new CGJunit(mapHTMLCollection(rootNodes[0].children, CGJunitSuite.fromXml));
        } else {
            return new CGJunit(mapHTMLCollection(rootNodes, CGJunitSuite.fromXml));
        }
    }
}
