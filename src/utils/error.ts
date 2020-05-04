import { AxiosError } from 'axios';

import { hasAttr } from '@/utils/typed';

export function getErrorMessage(err: Error | AxiosError<any> | any): string {
    let msg;

    if (err == null) {
        // TODO: Find out why we have this case, and eliminate it because it
        // does not really make sense to throw a `null`.
        return '';
    }

    const httpErr = (err as AxiosError<any>)?.response?.data?.message;
    if (httpErr != null) {
        // TODO: Should we rewrite this case in terms of instanceof?
        msg = httpErr;
    } else if (err instanceof Error) {
        // TODO: Why do we log the error in this case, but not in the other
        // cases?
        // eslint-disable-next-line
        console.error(err);
        msg = err.message;
    } else {
        // TODO: Find out why we have this case, and eliminate its use by just
        // throwing errors.
        msg = err.toString();
    }

    return msg ?? 'Something unknown went wrong';
}

// Error handler is generic in the type of error and its return type.
type ErrorHandler<E extends Error, T> = (e: E) => T;

// An HTTP error handler should return a value of the same type as the response
// that triggered.
// TODO: Can/should we make this a dependent type, e.g. HttpErrorHandler<S, T>
// where S is the response status code, so that we can only create e.g. a 400
// handler that handles 400 responses? This may be difficult because not all
// errors have a response, and thus a status code.
type HttpErrorHandler<T> = ErrorHandler<AxiosError<T>, T>;

// Mapping from HTTP status code to error handler to run when an error with
// that status code occurs.
// TODO: Maybe it should also be possible to filter on the error codes defined
// in psef/exceptions.py::APICodes.
type HttpErrorHandlers<T> = {
    [status: number]: HttpErrorHandler<T>;
    default?: HttpErrorHandler<T>;
    noResponse?: HttpErrorHandler<T>;
};

export function handleHttpError<T>(handlers: HttpErrorHandlers<T>, err: AxiosError<T>): T {
    const status = err.response?.status;

    if (status != null) {
        if (hasAttr(handlers, status.toString())) {
            return handlers[status](err);
        }

        const defaultHandler = handlers?.default;
        if (defaultHandler != null) {
            return defaultHandler(err);
        }
    }

    const noResHandler = handlers?.noResponse;
    if (noResHandler != null) {
        return noResHandler(err);
    }

    throw err;
}
