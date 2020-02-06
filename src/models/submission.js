/* SPDX-License-Identifier: AGPL-3.0-only */
import {
    cmpNoCase,
    getProps,
    setProps,
    formatGrade,
    snakeToCamelCase,
    readableFormatDate,
    coerceToString,
} from '@/utils';
import moment from 'moment';
import { store } from '@/store';
import * as mutationTypes from '@/store/mutation-types';

const REVISIONS = ['student', 'teacher'];

// eslint-disable-next-line
export class FileTree {
    constructor(
        studentTree,
        teacherTree,
        diff,
        flattened,
        revisionCache = {},
        autoTestTree = null,
    ) {
        this.student = Object.freeze(studentTree);
        this.teacher = Object.freeze(teacherTree);
        this.diff = Object.freeze(diff);
        this.flattened = Object.freeze(flattened);
        this._revisionCache = revisionCache;
        this.autotest = Object.freeze(autoTestTree);
        Object.freeze(this);
    }

    addAutoTestTree(autoTestTree) {
        return new FileTree(
            this.student,
            this.teacher,
            this.diff,
            this.flattened,
            this._revisionCache,
            autoTestTree,
        );
    }

    static fromServerData(studentTree, teacherTree) {
        let diff;
        if (teacherTree) {
            diff = FileTree.matchFiles(studentTree, teacherTree);
        } else {
            diff = FileTree.matchFiles(studentTree, studentTree);
        }

        const flattened = FileTree.flatten(diff);
        return new FileTree(studentTree, teacherTree, diff, flattened);
    }

    static matchFiles(tree1, tree2) {
        const diffTree = {
            name: tree1.name,
            entries: [],
            push(ids, name) {
                this.entries.push({ ids, name });
            },
        };

        const doneIds = new Set();
        const lookupTree2 = tree2.entries.reduce((accum, cur) => {
            accum[cur.name] = cur;
            return accum;
        }, {});

        tree1.entries.forEach(self => {
            const other = lookupTree2[self.name];

            if (other == null) {
                self.revision = null;
                diffTree.push([self.id, null], self.name);
                return;
            }

            doneIds.add(other.id);

            if (self.id !== other.id) {
                self.revision = other;
                other.revision = self;
            }

            if (self.entries && other.entries) {
                diffTree.entries.push(FileTree.matchFiles(self, other));
            } else if (self.entries == null && other.entries == null) {
                diffTree.push([self.id, other.id], self.name);
            } else if (self.entries) {
                diffTree.push([null, other.id], other.name);
                diffTree.entries.push(
                    FileTree.matchFiles(self, {
                        name: self.name,
                        entries: [],
                    }),
                );
            } else if (other.entries) {
                diffTree.push([self.id, null], self.name);
                diffTree.entries.push(
                    FileTree.matchFiles(
                        {
                            name: other.name,
                            entries: [],
                        },
                        other,
                    ),
                );
            }
        });

        Object.values(lookupTree2).forEach(val => {
            if (doneIds.has(val.id)) {
                return;
            }
            if (val.entries) {
                diffTree.entries.push(
                    FileTree.matchFiles(
                        {
                            name: val.name,
                            entries: [],
                        },
                        val,
                    ),
                );
            } else {
                diffTree.push([null, val.id], val.name);
            }
        });

        diffTree.entries.sort((a, b) => {
            if (a.name === b.name) {
                return a.entries ? -1 : 1;
            }
            return cmpNoCase(a.name, b.name);
        });

        delete diffTree.push;
        return Object.freeze(diffTree);
    }

    static flatten(tree, prefix = []) {
        const filePaths = {};
        if (!tree || !tree.entries) {
            return {};
        }
        tree.entries.forEach(f => {
            if (f.entries) {
                const dirPaths = FileTree.flatten(f, prefix.concat(f.name));
                Object.assign(filePaths, dirPaths);
            } else {
                if (f.id != null) {
                    filePaths[f.id] = prefix.concat(f.name).join('/');
                }
                if (f.ids && f.ids[0] != null) {
                    filePaths[f.ids[0]] = prefix.concat(f.name).join('/');
                }
                if (f.ids && f.ids[1] != null) {
                    filePaths[f.ids[1]] = prefix.concat(f.name).join('/');
                }
            }
        });
        return filePaths;
    }

    hasRevision(f) {
        if (this._revisionCache[f.id] == null) {
            let res;
            if (f.entries) {
                res = this.dirHasRevision(f);
            } else {
                res = this.fileHasRevision(f);
            }

            this._revisionCache[f.id] = res;
        }
        return this._revisionCache[f.id];
    }

    // eslint-disable-next-line
    fileHasRevision(f) {
        if (f.entries) return false;

        return f.revision !== undefined || (f.ids && f.ids[0] !== f.ids[1]);
    }

    dirHasRevision(d) {
        if (d.revision !== undefined) {
            return true;
        }
        for (let i = 0; i < d.entries.length; i += 1) {
            if (this.hasRevision(d.entries[i])) {
                return true;
            }
        }
        return false;
    }

    // Returns the first file in the file tree that is not a folder
    // The file tree is searched with BFS
    getFirstFile(revision) {
        const tree = this[revision];

        if (!tree) {
            return null;
        }

        const queue = [tree];
        let candidate = null;
        let firstFound = null;

        while (queue.length > 0) {
            candidate = queue.shift();

            if (candidate.entries) {
                queue.push(...candidate.entries);
            } else {
                firstFound = firstFound || candidate;
                if (!candidate.name.startsWith('.')) {
                    return candidate;
                }
            }
        }

        // Well fuck it, lets simply return a broken file.
        return firstFound;
    }

    // Search the tree for the file with the givven id.
    search(revision, id) {
        return this.findFileInDir(this[revision], id);
    }

    getRevision(id) {
        return REVISIONS.find(rev => this.search(rev, id) != null);
    }

    // eslint-disable-next-line
    findFileInDir(tree, id) {
        if (!tree || !tree.entries || id == null) {
            return null;
        }
        const todo = [...tree.entries];

        for (let i = 0; todo.length > i; ++i) {
            const child = todo[i];
            if (
                child.id === id ||
                (child.revision && child.revision.id === id) ||
                (child.ids && (child.ids[0] === id || child.ids[1] === id))
            ) {
                return child;
            } else if (child.entries != null) {
                todo.push(...child.entries);
            }
        }
        return null;
    }
}

export class FeedbackLine {
    constructor(fileId, line, message, author) {
        // a fileId should never be a number.
        this.fileId = coerceToString(fileId);
        // A lineNumber should always be a number.
        this.line = Number(line);
        this.lineNumber = this.line;

        this.msg = message;
        this.authorId = null;

        if (author) {
            this.authorId = author.id;
            store.commit(`users/${mutationTypes.ADD_OR_UPDATE_USER}`, author);
        }

        Object.freeze(this);
    }

    get author() {
        return store.getters['users/getUser'](this.authorId);
    }
}

export class Feedback {
    constructor(general, linter, userLines) {
        this.general = general;
        this.linter = linter;
        this.userLines = Object.freeze(userLines);
        this.user = Object.freeze(
            this.userLines.reduce((acc, line) => {
                setProps(acc, line, line.fileId, line.lineNumber);
                return acc;
            }, {}),
        );

        Object.freeze(this);
    }

    static fromServerData(feedback) {
        const authors = feedback.authors;

        const general = getProps(feedback, null, 'general');
        const linter = getProps(feedback, {}, 'linter');

        const userLines = Object.entries(getProps(feedback, {}, 'user')).reduce(
            (lines, [fileId, fileFeedback]) => {
                lines.push(
                    ...Object.entries(fileFeedback).map(([line, lineFeedback]) => {
                        if (line instanceof FeedbackLine) {
                            return line;
                        } else {
                            return new FeedbackLine(
                                fileId,
                                line,
                                lineFeedback,
                                getProps(authors, null, fileId, line),
                            );
                        }
                    }),
                );
                return lines;
            },
            [],
        );
        return new Feedback(general, linter, userLines);
    }

    addFeedbackLine(line) {
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

    removeFeedbackLine(fileId, lineNumber) {
        return new Feedback(
            this.general,
            this.linter,
            this.userLines.filter(l => !(l.lineNumber === lineNumber && l.fileId === fileId)),
        );
    }
}

const SUBMISSION_SERVER_PROPS = ['id', 'origin', 'extra_info', 'grade_overridden', 'comment'];

const USER_PROPERTIES = ['user', 'assignee', 'comment_author'].reduce((acc, cur) => {
    acc[cur] = `${snakeToCamelCase(cur)}Id`;
    return acc;
}, {});

export class Submission {
    constructor(props) {
        Object.assign(this, props);
        this.grade = formatGrade(this.fullGrade);
        this.formattedCreatedAt = readableFormatDate(this.createdAt);
        Object.freeze(this);
    }

    static fromServerData(serverData, assignmentId) {
        const props = {};
        SUBMISSION_SERVER_PROPS.forEach(prop => {
            props[prop] = serverData[prop];
        });

        props.assignmentId = assignmentId;
        props.createdAt = moment.utc(serverData.created_at, moment.ISO_8601);
        props.fullGrade = serverData.grade;

        Object.entries(USER_PROPERTIES).forEach(([serverProp, idProp]) => {
            const user = serverData[serverProp];
            if (user != null) {
                props[idProp] = user.id;
                store.commit(`users/${mutationTypes.ADD_OR_UPDATE_USER}`, user);
            } else {
                props[idProp] = null;
            }
        });

        return new Submission(props);
    }

    get fileTree() {
        return store.getters['fileTrees/getFileTree'](this.assignmentId, this.id);
    }

    get feedback() {
        return store.getters['feedback/getFeedback'](this.assignmentId, this.id);
    }

    update(newProps) {
        return new Submission(
            Object.assign(
                {},
                this,
                Object.entries(newProps).reduce((acc, [key, val]) => {
                    if (key === 'id') {
                        throw TypeError(`Cannot set submission property: ${key}`);
                    } else if (key === 'grade') {
                        acc.fullGrade = val;
                    } else if (USER_PROPERTIES[key] != null) {
                        const prop = USER_PROPERTIES[key];

                        if (val) {
                            store.dispatch('users/addOrUpdateUser', { user: val });
                            acc[prop] = val.id;
                        } else {
                            acc[prop] = null;
                        }
                    } else {
                        acc[key] = val;
                    }

                    return acc;
                }, {}),
            ),
        );
    }

    get assignment() {
        return store.getters['courses/assignments'][this.assignmentId];
    }

    isLate() {
        if (this.assignment == null) {
            return false;
        }
        return this.createdAt.isAfter(this.assignment.deadline);
    }
}

Object.entries(USER_PROPERTIES).forEach(([serverProp, idProp]) => {
    Object.defineProperty(Submission.prototype, serverProp, {
        get() {
            return store.getters['users/getUser'](this[idProp]) || { id: null };
        },
        enumerable: false,
    });
});
