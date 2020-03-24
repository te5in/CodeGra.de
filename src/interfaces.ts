import { AxiosResponse } from 'axios';

export interface SubmitButtonResult<Y> extends AxiosResponse<any> {
    cgResult: Y;
}
