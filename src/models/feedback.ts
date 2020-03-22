// @ts-ignore
import { getProps, setProps, coerceToString } from '@/utils';
// @ts-ignore
import { store } from '@/store';
import { User, AnyUser } from './user';
// @ts-ignore

export class FeedbackReply {
    constructor(
        public readonly id: number,
        public readonly inReplyToId: number | null,
        public readonly message: string,
        public readonly authorId: number | null,
        public readonly hasEdits: boolean,
    ) {
        Object.freeze(this);
    }

    static fromServerData(serverData: any): FeedbackReply {
        return new FeedbackReply(
            serverData.id,
            serverData.in_reply_to_id,
            serverData.comment,
            serverData.author_id,
            serverData.has_edits,
        );
    }

    get author(): AnyUser | null {
        return User.findUserById(this.authorId);
    }
}

export class FeedbackLine {
    constructor(
        public readonly id: number | null,
        public readonly fileId: string,
        public readonly line: number,
        public readonly replies: ReadonlyArray<FeedbackReply>,
    ) {
        Object.freeze(this);
    }

    get lineNumber(): number {
        return this.line;
    }

    static fromServerData(data: any): FeedbackLine {
        const replies = Object.freeze(data.replies.map(FeedbackReply.fromServerData));
        return new FeedbackLine(data.id, coerceToString(data.file_id), data.line, replies);
    }

    updateReply(updatedReply: FeedbackReply): FeedbackLine {
        const replies = this.replies.map(r => {
            if (r.id === updatedReply.id) {
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
}

export class Feedback {
    readonly userLines: ReadonlyArray<FeedbackLine>;

    readonly user: { [key: string]: { [key: number]: FeedbackLine } };

    constructor(
        public readonly general: string | null,
        public readonly linter: any,
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

    static fromServerData(feedback: any): Feedback {
        getProps(feedback, [], 'authors').forEach((author: any) => {
            store.dispatch('users/addOrUpdateUser', { user: author });
        });

        const general = getProps(feedback, null, 'general');
        const linter = getProps(feedback, {}, 'linter');

        const userLines = getProps(feedback, [], 'user').map((line: FeedbackLine | any) => {
            if (line instanceof FeedbackLine) {
                return line;
            } else {
                return FeedbackLine.fromServerData(line);
            }
        });

        return new Feedback(general, linter, userLines);
    }

    addFeedbackLine(line: FeedbackLine): Feedback {
        if (!(line instanceof FeedbackLine)) {
            throw new Error('The given line is not the correct class');
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

    removeFeedbackLine(fileId: string, lineNumber: number): Feedback {
        return new Feedback(
            this.general,
            this.linter,
            this.userLines.filter(l => !(l.lineNumber === lineNumber && l.fileId === fileId)),
        );
    }
}
