import { AxiosResponse } from 'axios';

export interface SubmitButtonResult<Y, T = any> extends AxiosResponse<T> {
    cgResult: Y;

    onAfterSuccess?: () => void;
}
