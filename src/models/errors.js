export class ValidationError {
    // eslint-disable-next-line class-methods-use-this
    get hasErrors() {
        return false;
    }

    throwOnError() {
        if (this.hasErrors) {
            // eslint-disable-next-line no-throw-literal
            throw this;
        }
    }
}

export class RubricRowValidationError extends ValidationError {
    constructor() {
        super();

        this.categories = [];
        this.continuous = [];
        this.itemHeader = [];
        this.itemPoints = [];
        this.unnamed = false;
        this.maxPoints = false;
        Object.seal(this);
    }

    get hasErrors() {
        return (
            this.categories.length > 0 ||
            this.continuous.length > 0 ||
            this.itemHeader.length > 0 ||
            this.itemPoints.length > 0 ||
            this.unnamed ||
            this.maxPoints
        );
    }
}

export class RubricResultValidationError extends ValidationError {
    constructor() {
        super();

        this.multipliers = [];
        Object.seal(this);
    }

    get hasErrors() {
        return this.multipliers.length > 0;
    }
}
