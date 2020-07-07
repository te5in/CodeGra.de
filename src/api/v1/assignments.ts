import * as models from '@/models';
import axios, { AxiosResponse } from 'axios';

interface PeerFeebackConnection {
    subject: models.UserServerData;
    peer: models.UserServerData;
}

export function getPeerFeebackSubjects(
    assignmentId: number,
    userId: number,
): Promise<AxiosResponse<PeerFeebackConnection[]>> {
    return axios.get(`/api/v1/assignments/${assignmentId}/users/${userId}/peer_feedback_subjects/`);
}

export function getCommentsByUser(
    assignmentId: number,
    userId: number,
): Promise<AxiosResponse<models.FeedbackLineServerData[]>> {
    return axios.get(`/api/v1/assignments/${assignmentId}/users/${userId}/comments/`);
}
