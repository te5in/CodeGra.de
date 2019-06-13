// eslint-disable-next-line
export function ensurePythonRegexHasCaptureGroup(regex) {
    let nesting = 0;
    let hasGroup = false;

    for (let i = 0; i < regex.length; i++) {
        switch (regex[i]) {
            case '\\':
                i++;
                break;
            case '(':
                nesting++;
                if (regex[i + 1] !== '?') {
                    hasGroup = true;
                } else if (regex[i + 2] === 'P') {
                    hasGroup = true;
                    i += 2;
                }
                break;
            case ')':
                if (nesting === 0) {
                    throw new Error('Unbalanced parentheses.');
                }
                nesting--;
                break;
            default:
                break;
        }
    }

    if (nesting !== 0) {
        throw new Error('Unbalanced parentheses.');
    }

    if (!hasGroup) {
        throw new Error('Regular expression does not have a capture group.');
    }

    return true;
}
