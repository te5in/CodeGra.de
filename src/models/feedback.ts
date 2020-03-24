import * as moment from 'moment';
import axios from 'axios';

// @ts-ignore
import { setProps, coerceToString, getUniqueId } from '@/utils';

import { store } from '@/store';
import { SubmitButtonResult } from '../interfaces.ts';

// @ts-ignore

import { User, AnyUser, UserServerData } from './user';

type ReplyTypes = 'plain_text' | 'markdown';

/* eslint-disable camelcase */
interface FeedbackReplyServerData {
    id: number;
    comment: string;
    author_id: number | null;
    in_reply_to_id: number | null;
    has_edits: boolean;
    created_at: string;
    updated_at: string;
    reply_type: ReplyTypes;
}

interface FeedbackLineServerData {
    id: number;
    file_id: number;
    line: number;
    replies: FeedbackReplyServerData[];
}

type LinterFeedbackServerData = Record<string, Record<string, [string, Record<string, any>][]>>;

interface FeedbackServerData {
    general: string | null;
    linter: LinterFeedbackServerData;
    user: Array<FeedbackLine | FeedbackLineServerData>;
    authors: UserServerData[];
}
/* eslint-enable camelcase */

export class FeedbackReply {
    constructor(
        public readonly trackingId: number,
        public readonly id: number | null,
        public readonly inReplyToId: number | null,
        public readonly message: string,
        public readonly authorId: number | null,
        public readonly hasEdits: boolean,
        public readonly replyType: ReplyTypes,
        public readonly createdAt: moment.Moment,
        public readonly updatedAt: moment.Moment,
        private readonly feedbackLineId: number,
        public readonly deleted = false,
    ) {
        Object.freeze(this);
    }

    static fromServerData(
        serverData: FeedbackReplyServerData,
        feedbackLineId: number,
        trackingId: number = getUniqueId(),
    ): FeedbackReply {
        return new FeedbackReply(
            trackingId,
            serverData.id,
            serverData.in_reply_to_id,
            serverData.comment,
            serverData.author_id,
            serverData.has_edits,
            serverData.reply_type,
            moment.utc(serverData.created_at, moment.ISO_8601),
            moment.utc(serverData.updated_at, moment.ISO_8601),
            feedbackLineId,
        );
    }

    updateFromServerData(serverData: FeedbackReplyServerData): FeedbackReply {
        return FeedbackReply.fromServerData(serverData, this.feedbackLineId, this.trackingId);
    }

    get author(): AnyUser | null {
        return User.findUserById(this.authorId);
    }

    get isEmpty(): boolean {
        return !this.message;
    }

    update(message: string): FeedbackReply {
        return new FeedbackReply(
            this.trackingId,
            this.id,
            this.inReplyToId,
            message,
            this.authorId,
            this.hasEdits,
            this.replyType,
            this.createdAt,
            this.updatedAt,
            this.feedbackLineId,
        );
    }

    markAsDeleted() {
        return new FeedbackReply(
            this.trackingId,
            this.id,
            this.inReplyToId,
            this.message,
            this.authorId,
            this.hasEdits,
            this.replyType,
            this.createdAt,
            this.updatedAt,
            this.feedbackLineId,
            true, // Deleted
        );
    }

    delete(): Promise<object> {
        if (this.id == null) {
            return Promise.resolve({});
        }
        return axios.delete(`/api/v1/comments/${this.feedbackLineId}/replies/${this.id}`);
    }

    save(): Promise<object> {
        if (this.id == null) {
            return axios.post(`/api/v1/comments/${this.feedbackLineId}/replies/`, {
                comment: this.message,
                in_reply_to_id: this.inReplyToId,
                reply_type: this.replyType,
            });
        } else {
            return axios.patch(`/api/v1/comments/${this.feedbackLineId}/replies/${this.id}`, {
                comment: this.message,
            });
        }
    }

    static createEmpty(userId: number, feedbackLineId: number): FeedbackReply {
        return new FeedbackReply(
            getUniqueId(),
            null,
            null,
            '',
            userId,
            false,
            'markdown',
            moment(),
            moment(),
            feedbackLineId,
        );
    }
}

export class FeedbackLine {
    constructor(
        public readonly id: number,
        public readonly fileId: string,
        public readonly line: number,
        public readonly replies: ReadonlyArray<FeedbackReply>,
    ) {
        Object.freeze(this);
    }

    get isEmpty(): boolean {
        return !this.replies.some(reply => !reply.deleted);
    }

    get lineNumber(): number {
        return this.line;
    }

    static fromServerData(data: FeedbackLineServerData): FeedbackLine {
        const replies = Object.freeze(
            data.replies.map(r => FeedbackReply.fromServerData(r, data.id)),
        );
        return new FeedbackLine(data.id, coerceToString(data.file_id), data.line, replies);
    }

    deleteReply(updatedReply: FeedbackReply): FeedbackLine {
        const replies = this.replies.map(r => {
            if (r.trackingId === updatedReply.trackingId) {
                return r.markAsDeleted();
            }
            return r;
        });
        return new FeedbackLine(this.id, this.fileId, this.line, Object.freeze(replies));
    }

    updateReply(updatedReply: FeedbackReply): FeedbackLine {
        const replies = this.replies.map(r => {
            if (r.trackingId === updatedReply.trackingId) {
                return updatedReply;
            }
            return r;
        });
        return new FeedbackLine(this.id, this.fileId, this.line, Object.freeze(replies));
    }

    addReply(newReply: FeedbackReply): FeedbackLine {
        return new FeedbackLine(
            this.id,
            this.fileId,
            this.line,
            Object.freeze(this.replies.concat(newReply)),
        );
    }

    static createFeedbackLine(
        fileId: number,
        line: number,
        userId: number,
    ): Promise<SubmitButtonResult<FeedbackLine>> {
        return axios
            .post('/api/v1/comments/', {
                file_id: fileId,
                line,
            })
            .then(response => {
                const feedbackLine = FeedbackLine.fromServerData(response.data);
                return {
                    ...response,
                    cgResult: feedbackLine.addReply(
                        FeedbackReply.createEmpty(userId, feedbackLine.id),
                    ),
                };
            });
    }
}

export class Feedback {
    readonly userLines: ReadonlyArray<FeedbackLine>;

    readonly user: { [key: string]: { [key: number]: FeedbackLine } };

    constructor(
        public readonly general: string | null,
        public readonly linter: LinterFeedbackServerData,
        userLines: FeedbackLine[],
    ) {
        this.userLines = Object.freeze(userLines);

        this.user = Object.freeze(
            this.userLines.reduce((acc, line) => {
                setProps(acc, line, line.fileId, line.lineNumber);
                return acc;
            }, {}),
        );

        Object.freeze(this);
    }

    static fromServerData(feedback?: FeedbackServerData): Feedback {
        if (feedback?.authors) {
            feedback.authors.forEach(author => {
                store.dispatch('users/addOrUpdateUser', { user: author });
            });
        }

        const general = feedback?.general ?? null;
        const linter = feedback?.linter ?? {};

        const userLines =
            feedback?.user.map((line: FeedbackLine | any) => {
                if (line instanceof FeedbackLine) {
                    return line;
                } else {
                    return FeedbackLine.fromServerData(line);
                }
            }) ?? [];

        return new Feedback(general, linter, userLines);
    }

    addFeedbackLine(line: FeedbackLine): Feedback {
        if (!(line instanceof FeedbackLine)) {
            throw new Error(
                // @ts-ignore
                `The given line is not the correct class, got ${line.constructor.name}`,
            );
        }

        const newLines = [...this.userLines];
        const oldLineIndex = this.userLines.findIndex(
            l => l.lineNumber === line.lineNumber && l.fileId === line.fileId,
        );
        if (oldLineIndex < 0) {
            newLines.push(line);
        } else {
            newLines[oldLineIndex] = line;
        }

        return new Feedback(this.general, this.linter, newLines);
    }

    removeFeedbackLine(line: FeedbackLine): Feedback {
        return new Feedback(
            this.general,
            this.linter,
            this.userLines.filter(
                l => !(l.lineNumber === line.lineNumber && l.fileId === line.fileId),
            ),
        );
    }

    getFeedbackLine(fileId: string, lineNumber: number): FeedbackLine {
        return this.user[fileId][lineNumber];
    }
}
