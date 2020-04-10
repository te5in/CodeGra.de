/* SPDX-License-Identifier: AGPL-3.0-only */
import { AxiosResponse } from 'axios';

export interface SubmitButtonResult<Y, T = any> extends AxiosResponse<T> {
    cgResult: Y;

    onAfterSuccess?: () => void;
}

interface BaseSnippet {
    id: number;
    key: string;
    value: string;
}

export interface UserSnippet extends BaseSnippet {
    course: undefined;
}

export interface CourseSnippet extends BaseSnippet {
    course: true;
}

export type Snippet = UserSnippet | CourseSnippet;
