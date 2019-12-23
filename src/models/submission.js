import { cmpNoCase } from '@/utils';

const REVISIONS = ['student', 'teacher'];

// eslint-disable-next-line
export class FileTree {
    constructor(studentTree, teacherTree) {
        this.student = studentTree;
        this.teacher = teacherTree;

        if (teacherTree) {
            this.diff = this.matchFiles(studentTree, teacherTree);
        } else {
            this.diff = this.matchFiles(studentTree, studentTree);
        }

        this.flattened = this.flatten(this.diff);
        this.revisionCache = {};
    }

    matchFiles(tree1, tree2) {
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
                diffTree.entries.push(this.matchFiles(self, other));
            } else if (self.entries == null && other.entries == null) {
                diffTree.push([self.id, other.id], self.name);
            } else if (self.entries) {
                diffTree.push([null, other.id], other.name);
                diffTree.entries.push(
                    this.matchFiles(self, {
                        name: self.name,
                        entries: [],
                    }),
                );
            } else if (other.entries) {
                diffTree.push([self.id, null], self.name);
                diffTree.entries.push(
                    this.matchFiles(
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
                    this.matchFiles(
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
        return diffTree;
    }

    flatten(tree, prefix = []) {
        const filePaths = {};
        if (!tree || !tree.entries) {
            return {};
        }
        tree.entries.forEach(f => {
            if (f.entries) {
                const dirPaths = this.flatten(f, prefix.concat(f.name));
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
        if (this.revisionCache[f.id] == null) {
            let res;
            if (f.entries) {
                res = this.dirHasRevision(f);
            } else {
                res = this.fileHasRevision(f);
            }

            this.revisionCache[f.id] = res;
        }
        return this.revisionCache[f.id];
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

export class Feedback {
    constructor(feedback) {
        Object.assign(this, feedback);

        Object.entries(this.user).forEach(([fileId, fileFeedback]) => {
            Object.keys(fileFeedback).forEach(line => {
                fileFeedback[line] = {
                    line,
                    msg: fileFeedback[line],
                    author: this.authors ? this.authors[fileId][line] : null,
                };
            });
        });
    }
}
