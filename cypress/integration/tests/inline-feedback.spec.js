context('Inline feedback', () => {
    const unique = Math.floor(100000 * Math.random());
    let course;
    let assignment;
    let submission;

    const inlineMsg = 'Inline feedback message';
    const otherMsg = 'Other feedback message';

    function waitUntilLoaded() {
        cy.wait('@getPermissionsRoute');
        cy.get('.page.submission').should('be.visible');
    }

    function login(username, password) {
        cy.login(username, password);
        waitUntilLoaded();
    }

    function reload() {
        cy.reload();
        waitUntilLoaded();
    }

    function getFileViewer(viewer) {
        return cy.get(`.file-viewer${viewer}`);
    }

    function openFile(filename, viewer='.file-viewer') {
        cy.get('.file-tree')
            .contains('.file a', filename)
            .click({ force: true });

        getFileViewer(viewer).should('be.visible');
        cy.get(`.file-viewer${viewer} > .loader`).should('not.exist');
    }

    function getLine(line, viewer='.code-viewer') {
        return getFileViewer(viewer).find(`.line:nth-child(${line + 1})`);
    }

    function checkInlineFeedback(line, feedback, checkAfterReload=false, viewer=undefined) {
        if (feedback == null) {
            getLine(line, viewer)
                .find('.feedback-area .feedback-reply .markdown-message')
                .should('not.exist');
        } else {
            getLine(line, viewer)
                .find('.feedback-area .feedback-reply .markdown-message')
                .scrollIntoView()
                .should('be.visible')
                .should('contain', feedback);
        }

        if (checkAfterReload) {
            reload();
            checkInlineFeedback(line, feedback, false, viewer);
        }
    }

    function startCreate(line, viewer='.file-viewer') {
        const base = '.feedback-area .feedback-reply'

        getLine(line, viewer)
            .click()
        cy.wait('@addCommentRoute')

        return cy
            .get(`.file-viewer${viewer} li:nth-child(${line + 1}) ${base} .snippetable-input textarea:focus`)
            .should('be.visible');
    }


    function startEdit(line, viewer='.file-viewer') {
        const base = '.feedback-area .feedback-reply'

        getLine(line, viewer)
            .find(`${base}:not(.editing) .edit-buttons-wrapper .btn[name=edit-feedback]`)
            .click();

        return cy.get(`.file-viewer${viewer} li:nth-child(${line + 1}) ${base} .snippetable-input textarea:focus`);
    }

    function editInlineFeedback(
        line,
        feedback,
        submitOpts={},
        viewer='.file-viewer',
    ) {
        const opts = Object.assign({
            waitForDefault: false,
        }, submitOpts);

        const base = '.feedback-area .feedback-reply'

        startEdit(line, viewer)
            .setText(feedback);
        getLine(line, viewer)
            .find(`${base}.editing .submit-button[name=submit-feedback]`)
            .submit('success', opts);
        getLine(line, viewer)
            .find('.feedback-reply.editing')
            .should('not.exist');
    }

    function giveInlineFeedback(
        line,
        feedback,
        submitOpts={},
        viewer=undefined,
    ) {
        const opts = Object.assign({
            waitForDefault: false,
        }, submitOpts);
        const base = '.feedback-area .feedback-reply'

        startCreate(line, viewer)
            .setText(feedback);
        getLine(line, viewer)
            .find(`${base} .submit-button[name=submit-feedback]`)
            .submit('success', opts);
        getLine(line, viewer)
            .find('.feedback-reply.editing')
            .should('not.exist');
    }

    function deleteInlineFeedback(
        line,
        submitOpts,
        viewer=undefined,
    ) {
        const opts = Object.assign({
            waitForState: false,
            waitForDefault: false,
        }, submitOpts);

        getLine(line, viewer)
            .click()
            .find('.feedback-reply:not(.editing)')
            .should('be.visible');

        getLine(line, viewer)
            .find(`.feedback-reply:not(.editing) .edit-buttons-wrapper .btn[name=delete-feedback]`)
            .submit('success', {
                waitForState: false,
                waitForDefault: false,
                hasConfirm: true,
            });

        getLine(line, viewer)
            .find('.feedback-reply')
            .should('not.exist');
    }

    function checkInlineFeedbackOverview(filename, line, feedback) {
        getOverviewFile(filename)
            .find('.inner-code-viewer')
            .should('be.visible')
            .find(`.line:nth-child(${line + 1}) .feedback-reply .markdown-message`)
            .should('contain', feedback);
    }

    function getSingleFeedbackButton(viewer='.file-viewer') {
        return getFileViewer(viewer).find('.feedback-button');
    }

    function editSingleFeedback(viewer) {
        getSingleFeedbackButton(viewer).click({ force: true });
    }

    function getSingleFeedbackArea(cls, viewer='.file-viewer') {
        const el = getFileViewer(viewer)
              .find('.feedback-area .feedback-reply');
        if (cls === 'non-editing') {
                return el.should('have.not.class', cls);
        } else {
                return el.should('have.class', cls);
        }
    }

    function checkSingleFeedback(feedback, checkAfterReload=false, viewer='.file-viewer') {
        if (feedback == null) {
            getFileViewer(viewer)
                .find('.feedback-area')
                .should('not.exist');
        } else {
            getSingleFeedbackArea('non-editing', viewer)
                .should('contain', feedback);
        }

        if (checkAfterReload) {
            reload();
            checkSingleFeedback(feedback, false, viewer);
        }
    }

    function giveSingleFeedback(feedback, viewer) {
        editSingleFeedback(viewer);
        getSingleFeedbackArea('editing', viewer)
            .find('textarea:focus')
            .clear()
            .setText(feedback);
        getSingleFeedbackArea('editing', viewer)
            .find('.submit-button[name=submit-feedback]')
            .submit('success', { waitForDefault: false });
    }

    function deleteSingleFeedback(viewer) {
        return getSingleFeedbackArea('non-editing', viewer)
            .find(`.edit-buttons-wrapper .btn[name=delete-feedback]`)
            .submit('success', {
                waitForState: false,
                waitForDefault: false,
                hasConfirm: true,
            });
    }

    function scrollToBottom() {
        return cy.get('.file-viewer .floating-feedback-button .content-wrapper *')
            .last()
            .scrollIntoView();
    }

    function checkSingleFeedbackOverview(filename, feedback) {
        cy.openCategory('Feedback overview');
        getOverviewFile(filename)
            .should('contain', 'Overview mode is not available');
        if (feedback != null) {
            getOverviewFile(filename)
                .find('.feedback-area')
                .should('contain', feedback);
        }
    }

    function checkSingleFeedbackOverviewLink(filename) {
        function baseUrl(url) {
            return url.replace(/[?#].*/, '');
        }

        cy.url().then(url => {
            cy.openCategory('Feedback overview');
            getOverviewFile(filename)
                .contains('.inline-link', 'here')
                .click();
            cy.url().then(newUrl => {
                cy.wrap(baseUrl(newUrl)).should('eq', baseUrl(url));
            });
        });
    }

    function checkOverviewBadge(n) {
        if (n > 0) {
            cy.get('.categories')
                .contains('.category', 'Feedback overview')
                .find('.badge')
                .should('contain', n.toString());
        } else {
            cy.get('.categories')
                .contains('.category', 'Feedback overview')
                .find('.badge')
                .should('not.exist');
        }
    }

    function getOverviewFile(filename) {
        return cy.get('.feedback-overview')
            .contains('.card-header', filename)
            .parent()
    }

    before(() => {
        cy.visit('/');

        cy.createCourse(
            `Inline feedback Course ${unique}`,
            [{ name: 'student1', role: 'Student' }],
        ).then(res => {
            course = res;
            return cy.createAssignment(
                course.id,
                `Inline feedback Assignment ${unique}`,
                { deadline: 'tomorrow', state: 'open' },
            );
        }).then(res => {
            assignment = res;
            return cy.createSubmission(
                assignment.id,
                'test_submissions/all_filetypes.zip',
                { author: 'student1' },
            );
        }).then(res => {
            submission = res;
            cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions/${submission.id}`);
        });
    });

    beforeEach(() => {
        cy.server();
        cy.route('/api/v1/login?type=extended&with_permissions').as('getPermissionsRoute');
        cy.route('POST', '/api/v1/comments/').as('addCommentRoute');
        login('admin', 'admin');
    });

    context('CodeViewer', () => {
        const filename = 'timer.c';

        beforeEach(() => {
            cy.openCategory('Code');
            openFile(filename, '.code-viewer');
        });

        it('should be possible to give inline feedback', () => {
            giveInlineFeedback(0, inlineMsg, {});
            checkInlineFeedback(0, inlineMsg, true);
            getLine(0)
                .find('.info-text-wrapper sup')
                .should('not.exist');

            editInlineFeedback(0, otherMsg, {});
            checkInlineFeedback(0, otherMsg, true);
            getLine(0)
                .find('.info-text-wrapper sup')
                .scrollIntoView()
                .should('be.visible')
                .then($elem => {
                    cy.wrap($elem.attr('title')).should('contain', 'Edited on');
                });
        });

        it('should be possible to submit feedback on ctrl+enter', () => {
            getLine(0)
                .click()
                .find('.feedback-reply:not(.editing)')
                .should('be.visible');
            startEdit(0);
            cy.get('.file-viewer li:nth-child(1) .feedback-reply .snippetable-input textarea')
                .focus()
                .setText(`${inlineMsg}{ctrl}{enter}`);
            checkInlineFeedback(0, inlineMsg);
        });

        it('should be visible to students when the assignment is done', () => {
            editInlineFeedback(0, inlineMsg);
            checkInlineFeedback(0, inlineMsg);

            login('student1', 'Student1');
            checkInlineFeedback(0, null);

            cy.tempPatchAssignment(assignment, { state: 'done' }, () => {
                waitUntilLoaded();
                cy.openCategory('Code');
                checkInlineFeedback(0, inlineMsg);
                cy.openCategory('Feedback overview');
                checkInlineFeedbackOverview(filename, 0, inlineMsg);
            });
        });

        context('Deleting', () => {
            let line = 0;
            beforeEach(() => {
                cy.openCategory('Code');
                openFile(filename, '.code-viewer');
                line += 1;
            });

            it('should delete with confirmation if feedback is not empty', () => {
                reload();
                openFile(filename, '.code-viewer');
                giveInlineFeedback(line, inlineMsg);

                startEdit(line);
                getLine(line)
                    .find('.feedback-reply .submit-button[name=delete-feedback]')
                    .submit('success', { hasConfirm: true, waitForDefault: false });
                checkInlineFeedback(line, null);

                // Check that adding works after deleting.
                giveInlineFeedback(line, inlineMsg);
                checkInlineFeedback(line, inlineMsg);
            });

            it('should delete without confirmation if feedback is empty', () => {
                startCreate(line);

                getLine(line).find('.submit-button[name=delete-feedback]')
                    .submit('success', { hasConfirm: false, waitForDefault: false });
                checkInlineFeedback(line, null);
                // Check that adding works after deleting.
                giveInlineFeedback(line, inlineMsg);
                checkInlineFeedback(line, inlineMsg);
            });

            it('should delete by submitting if feedback is empty', () => {
                giveInlineFeedback(line, null, { waitForState: true });
                checkInlineFeedback(line, null);

                // Check that adding works after deleting.
                giveInlineFeedback(line, inlineMsg);
                checkInlineFeedback(line, inlineMsg);
            });

            it('should be possible to delete by the gear icon', () => {
                giveInlineFeedback(line, inlineMsg);
                checkInlineFeedback(line, inlineMsg);
                deleteInlineFeedback(line);
                checkInlineFeedback(line, null);
            })
        });

        context('Feedback overview', () => {
            it('should show a badge in the category if there is inline feedback', () => {
                checkOverviewBadge(0);
                giveInlineFeedback(0, otherMsg);
                checkOverviewBadge(1);

                editInlineFeedback(0, inlineMsg);
                checkOverviewBadge(1);

                giveInlineFeedback(1, otherMsg);
                checkOverviewBadge(2);

                cy.openCategory('Feedback overview');
                checkInlineFeedbackOverview(filename, 0, inlineMsg);
                checkInlineFeedbackOverview(filename, 1, otherMsg);

                cy.openCategory('Code');
                deleteInlineFeedback(0);
                checkOverviewBadge(1);
                deleteInlineFeedback(1);
                checkOverviewBadge(0);
            });

            it('should show a message if no inline feedback is given', () => {
                cy.openCategory('Feedback overview');
                cy.get('.inline-feedback')
                    .should('contain', 'This submission has no line comments.');
            });
        });

        context('IPython code cells', () => {
            const filename = 'Graaf vinden met diameter%avg-path-length ratio.ipynb';
            const selector = '.ipython-viewer .inner-code-viewer:first';

            beforeEach(() => {
                openFile(filename, '.ipython-viewer');
            });

            it('should be possible to give inline feedback', () => {
                giveInlineFeedback(0, inlineMsg, {}, selector);
                checkInlineFeedback(0, inlineMsg, true, selector);
            });

            it('should be possible to delete inline feedback', () => {
                editInlineFeedback(0, inlineMsg, {}, selector);
                deleteInlineFeedback(0, null, selector);
                checkInlineFeedback(0, null, true, selector);
            });
        });
    });

    context('Single feedback viewers', () => {
        const files = {
            ImageViewer: {
                filename: 'venn1.png',
                outerViewer: '.image-viewer',
                checkMessageInOverview: true,
            },
            IPythonMarkdownCell: {
                filename: 'Graaf vinden met diameter%avg-path-length ratio.ipynb',
                outerViewer: '.ipython-viewer',
                innerViewer: '.ipython-viewer .markdown-wrapper:first',
            },
            IPythonResultCell: {
                filename: 'Graaf vinden met diameter%avg-path-length ratio.ipynb',
                outerViewer: '.ipython-viewer',
                innerViewer: '.ipython-viewer .result-cell:first',
            },
            MarkdownViewer: {
                filename: 'README.md',
                outerViewer: '.markdown-viewer',
                checkMessageInOverview: true,
            },
            PDFViewer: {
                filename: 'thomas-schaper-version1.pdf',
                outerViewer: '.pdf-viewer',
                checkMessageInOverview: true,
            },
        };

        beforeEach(() => {
            cy.openCategory('Code');
        });

        it('should be possible to give inline feedback', () => {
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                giveSingleFeedback(inlineMsg, opts.innerViewer);
                checkSingleFeedback(inlineMsg, false, opts.innerViewer);
            });
            reload();
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                checkSingleFeedback(inlineMsg, false, opts.innerViewer);
            });
        });

        it('should be possible to delete inline feedback', () => {
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                // giveSingleFeedback(inlineMsg, opts.innerViewer);
                getSingleFeedbackArea('non-editing', opts.innerViewer);
                deleteSingleFeedback(opts.innerViewer);
                checkSingleFeedback(null, false, opts.innerViewer);
            });
            reload();
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                checkSingleFeedback(null, false, opts.innerViewer);
            });
        });

        it('should show the file and possibly the feedback in the feedback overview', () => {
            Object.values(files).forEach(opts => {
                cy.openCategory('Code');
                openFile(opts.filename, opts.outerViewer);
                giveSingleFeedback(inlineMsg, opts.innerViewer);
                const msg = opts.checkMessageInOverview ? inlineMsg : null;
                checkSingleFeedbackOverview(opts.filename, msg);
            });
        });

        it('should link back to the file on the overview page', () => {
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                giveSingleFeedback(inlineMsg, opts.innerViewer);
                checkSingleFeedbackOverviewLink(opts.filename);
            });
        });

        it('should be visible to students when the assignment is done', () => {
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                giveSingleFeedback(inlineMsg, opts.innerViewer);
            });

            login('student1', 'Student1');
            Object.values(files).forEach(opts => {
                openFile(opts.filename, opts.outerViewer);
                checkSingleFeedback(null, false, opts.innerViewer);
            });

            cy.tempPatchAssignment(assignment, { state: 'done' }, () => {
                waitUntilLoaded();
                Object.values(files).forEach(opts => {
                    cy.openCategory('Code');
                    openFile(opts.filename, opts.outerViewer);
                    checkSingleFeedback(inlineMsg, false, opts.innerViewer);
                    cy.openCategory('Feedback overview');
                    const msg = opts.checkMessageInOverview ? inlineMsg : null;
                    checkSingleFeedbackOverview(opts.filename, msg);
                });
            });
        });
    });
});
