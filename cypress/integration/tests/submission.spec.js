context('Submission page', () => {
    const unique = Math.floor(100000 * Math.random());
    let course;
    let assignment;
    let submission;

    const generalMsg = 'General feedback message';
    const inlineMsg = 'Inline feedback message';
    const otherMsg = 'Other feedback message';

    function waitUntilLoaded() {
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

    function toggleGeneralFeedbackArea() {
        cy.get('[id^="general-feedback-toggle"]').click();
        return cy.get('[id^="general-feedback-popover"]');
    }

    function showGeneralFeedbackArea() {
        return toggleGeneralFeedbackArea()
            .should('not.have.class', 'fade')
            .should('be.visible');
    }

    function hideGeneralFeedbackArea() {
        return toggleGeneralFeedbackArea()
            .should('not.be.visible');
    }

    function giveGeneralFeedback(feedback) {
        showGeneralFeedbackArea()
            .as('gfArea')
            .find('textarea')
            .setText(feedback)
        cy.get('@gfArea')
            .find('.submit-button')
            .submit('success');
    }

    function checkGeneralFeedbackArea(feedback) {
        showGeneralFeedbackArea()
            .find('textarea')
            .should('have.value', feedback);
        reload();
        showGeneralFeedbackArea()
            .find('textarea')
            .should('have.value', feedback);
    }

    function checkGeneralFeedbackOverview(feedback) {
        cy.get('.feedback-overview .general-feedback')
            .should('contain', feedback);
        reload();
        cy.get('.feedback-overview .general-feedback')
            .should('contain', feedback);
    }

    function getFileViewer(viewer) {
        return cy.get(`.file-viewer${viewer}`);
    }

    function openFile(filename, viewer='.file-viewer') {
        cy.get('.file-tree')
            .contains('.file a', filename)
            .click({ force: true });
        getFileViewer(viewer).should('be.visible');
    }

    function getLine(line, viewer='.code-viewer') {
        return getFileViewer(viewer).find(`.line:nth(${line})`);
    }

    function checkInlineFeedback(line, feedback, checkAfterReload=false, viewer=undefined) {
        if (feedback == null) {
            getLine(line, viewer)
                .find('.feedback-area.non-editable')
                .should('not.exist');
        } else {
            getLine(line, viewer)
                .find('.feedback-area.non-editable')
                .should('be.visible')
                .should('contain', feedback);
        }

        if (checkAfterReload) {
            reload();
            checkInlineFeedback(line, feedback, false, viewer);
        }
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

        getLine(line, viewer)
            .click()
            .find('.feedback-area.edit')
            .should('be.visible');
        getLine(line, viewer)
            .find('.feedback-area.edit textarea')
            .setText(feedback);
        getLine(line, viewer)
            .find('.feedback-area.edit .submit-feedback .submit-button')
            .submit('success', opts);
        getLine(line, viewer)
            .find('.feedback-area.edit')
            .should('not.exist');
    }

    function deleteInlineFeedback(
        line,
        feedback,
        submitOpts,
        viewer=undefined,
    ) {
        const opts = Object.assign({
            waitForState: false,
            waitForDefault: false,
        }, submitOpts);

        getLine(line, viewer)
            .click()
            .find('.feedback-area.edit')
            .should('be.visible');
        getLine(line, viewer)
            .find('.feedback-area.edit textarea')
            .setText(feedback);
        getLine(line, viewer)
            .find('.feedback-area.edit .submit-button.delete-feedback')
            .submit('success', opts);
        getLine(line, viewer)
            .find('.feedback-area.edit')
            .should('not.exist');
    }

    function checkInlineFeedbackOverview(filename, line, feedback) {
        getOverviewFile(filename)
            .find('.inner-code-viewer')
            .should('be.visible')
            .find(`.line:nth(${line}) .feedback-area.non-editable`)
            .should('contain', feedback);
    }

    function getSingleFeedbackButton(viewer='.file-viewer') {
        return getFileViewer(viewer).find('.feedback-button');
    }

    function editSingleFeedback(viewer) {
        getSingleFeedbackButton(viewer).click({ force: true });
    }

    function getSingleFeedbackArea(cls, viewer='.file-viewer') {
        return getFileViewer(viewer)
            .find('.feedback-area')
            .should('have.class', cls);
    }

    function checkSingleFeedback(feedback, checkAfterReload=false, viewer='.file-viewer') {
        if (feedback == null) {
            getFileViewer(viewer)
                .find('.feedback-area')
                .should('not.exist');
        } else {
            getSingleFeedbackArea('non-editable', viewer)
                .should('contain', feedback);
        }

        if (checkAfterReload) {
            reload();
            checkSingleFeedback(feedback, false, viewer);
        }
    }

    function giveSingleFeedback(feedback, viewer) {
        editSingleFeedback(viewer);
        getSingleFeedbackArea('edit', viewer)
            .find('textarea')
            .clear()
            .setText(feedback);
        getSingleFeedbackArea('edit', viewer)
            .find('.submit-feedback .submit-button')
            .submit('success', { waitForDefault: false });
    }

    function deleteSingleFeedback(viewer) {
        editSingleFeedback(viewer);
        getSingleFeedbackArea('edit', viewer)
            .find('.submit-button.delete-feedback')
            .submit('success', { hasConfirm: true, waitForState: false });
    }

    function scrollToBottom() {
        cy.get('.file-viewer .floating-feedback-button .content-wrapper')
            .scrollTo('bottom');
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

    function getGradeInput() {
        return cy.get('.grade-viewer input[name="grade-input"]');
    }

    function submitGrade(state, opts={}) {
        cy.get('.grade-viewer .submit-button.submit-grade-btn')
            .submit(state, opts);
    }

    function checkGrade(grade) {
        getGradeInput()
            .should('have.value', typeof grade == 'number' ? grade.toFixed(2) : '');
    }

    function typeGrade(grade, opts={}) {
        getGradeInput()
            .clear()
            .setText(grade.toString());
    }

    function giveGrade(grade) {
        typeGrade(grade);
        submitGrade('success');
        checkGrade(grade);
    }

    function giveInvalidGrade(grade, submitOpts) {
        typeGrade(grade, { force: true });
        submitGrade('error', submitOpts);
    }

    function deleteGrade() {
        cy.get('.grade-viewer .submit-button.delete-button')
            .submit('success', { hasConfirm: true });
        checkGrade(null);
    }

    before(() => {
        cy.visit('/');

        cy.createCourse(
            `Submission Page Course ${unique}`,
            [{ name: 'student1', role: 'Student' }],
        ).then(res => {
            course = res;
            return cy.createAssignment(
                course.id,
                `Submission Page Assignment ${unique}`,
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
        login('admin', 'admin');
    });

    context('General feedback', () => {
        beforeEach(() => {
            cy.openCategory('Feedback overview');
        });

        after(() => {
            login('admin', 'admin');
            cy.patchSubmission(submission.id, { feedback: '' });
        });

        it('should be possible to give general feedback', () => {
            giveGeneralFeedback(generalMsg);
            checkGeneralFeedbackArea(generalMsg);
            hideGeneralFeedbackArea();
            giveGeneralFeedback(otherMsg);
            checkGeneralFeedbackArea(otherMsg);
            hideGeneralFeedbackArea();
        });

        it('should be possible to give an empty general feedback message', () => {
            giveGeneralFeedback('');
            checkGeneralFeedbackArea('');
            hideGeneralFeedbackArea();
        });

        it('should show the general feedback in the feedback overview', () => {
            giveGeneralFeedback(generalMsg);
            checkGeneralFeedbackOverview(generalMsg);
        });

        it('should show a message in the feedback overview if no general feedback is given', () => {
            giveGeneralFeedback('');
            checkGeneralFeedbackOverview('No general feedback given.');
        });

        it('should show a badge in the "Feedback overview" tab title if general feedback is not empty', () => {
            giveGeneralFeedback('');
            checkOverviewBadge(0);
            giveGeneralFeedback(generalMsg);
            checkOverviewBadge(1);
        });

        it('should be visible to students when the assignment is done', () => {
            giveGeneralFeedback(generalMsg);

            login('student1', 'Student1');
            cy.get('.feedback-overview')
                .should('contain', 'The feedback is not yet available');

            cy.tempPatchAssignment(assignment, { state: 'done' }, () => {
                waitUntilLoaded();
                checkGeneralFeedbackOverview(generalMsg);
            });
        });

        it('should ask to save feedback when closing the popover', () => {
            showGeneralFeedbackArea()
                .find('textarea')
                .type('abc');
            toggleGeneralFeedbackArea();
            cy.get('[id^="submit-button-"][id$="-confirm-popover"]')
                .should('be.visible');
        });

        it('should not ask to save feedback when there are no changes', () => {
            showGeneralFeedbackArea();
            toggleGeneralFeedbackArea();
            cy.get('[id^="submit-button-"][id$="-confirm-popover"]')
                .should('not.exist');
        });

        it('should not clear the rubric upon saving general feedback', () => {
            cy.createRubric(assignment.id, [
                {
                    header: 'Category 1',
                    description: 'Category 1',
                    items: [
                        { points: 0, header: '0 points', description: '0 points' },
                        { points: 1, header: '1 points', description: '1 points' },
                        { points: 2, header: '2 points', description: '2 points' },
                        { points: 3, header: '3 points', description: '3 points' },
                    ],
                },
            ]);
            reload();

            cy.get('.grade-viewer .rubric-save-warning').should('not.exist');
            cy.get('.rubric-viewer .rubric-item:first').click();
            cy.get('.rubric-viewer .rubric-item:first').should('have.class', 'selected');
            cy.get('.grade-viewer .rubric-save-warning').should('be.visible');

            showGeneralFeedbackArea()
                .as('gfArea')
                .find('textarea')
                .type(generalMsg);
            cy.get('@gfArea')
                .find('.submit-button')
                .submit('success', { waitForDefault: false });

            cy.get('.rubric-viewer .rubric-item:first').should('have.class', 'selected');
            cy.get('.grade-viewer .rubric-save-warning').should('be.visible');

            cy.patchSubmission(submission.id, { feedback: '' });
            cy.deleteRubric(assignment.id);
        });
    });

    context('Inline feedback', () => {
        context('CodeViewer', () => {
            const filename = 'timer.c';

            beforeEach(() => {
                cy.openCategory('Code');
                openFile(filename, '.code-viewer');
            });

            it('should be possible to give inline feedback', () => {
                giveInlineFeedback(0, inlineMsg, {});
                cy.log('after giving');
                checkInlineFeedback(0, inlineMsg, true);

                giveInlineFeedback(0, otherMsg, {});
                checkInlineFeedback(0, otherMsg, true);
            });

            it('should be possible to submit feedback on ctrl+enter', () => {
                getLine(0)
                    .click()
                    .find('.feedback-area.edit')
                    .should('be.visible');
                getLine(0)
                    .find('.feedback-area.edit textarea')
                    .setText(`${inlineMsg}{ctrl}{enter}`);
                checkInlineFeedback(0, inlineMsg);
            });

            it('should be visible to students when the assignment is done', () => {
                giveInlineFeedback(0, inlineMsg);
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

            context('Deleting without submitting first', () => {
                before(() => {
                    login('admin', 'admin');
                    cy.openCategory('Code');
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                });

                afterEach(() => {
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                });

                it('should delete with confirmation if feedback is not empty', () => {
                    deleteInlineFeedback(0, inlineMsg, { hasConfirm: true });
                    checkInlineFeedback(0, null);
                    // Check that adding works after deleting.
                    giveInlineFeedback(0, inlineMsg);
                    checkInlineFeedback(0, inlineMsg);
                });

                it('should delete without confirmation if feedback is empty', () => {
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                    checkInlineFeedback(0, null);
                    // Check that adding works after deleting.
                    giveInlineFeedback(0, inlineMsg);
                    checkInlineFeedback(0, inlineMsg);
                });

                it('should delete by submitting if feedback is empty', () => {
                    giveInlineFeedback(0, null, { waitForState: false });
                    checkInlineFeedback(0, null);
                    // Check that adding works after deleting.
                    giveInlineFeedback(0, inlineMsg);
                    checkInlineFeedback(0, inlineMsg);
                });
            });

            context('Deleting after submitting', () => {
                before(() => {
                    login('admin', 'admin');
                    cy.openCategory('Code');
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                });

                afterEach(() => {
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                });

                it('should delete with confirmation if feedback is not empty', () => {
                    giveInlineFeedback(0, inlineMsg);
                    deleteInlineFeedback(0, inlineMsg, { hasConfirm: true });
                    checkInlineFeedback(0, null);
                    // Check that adding works after deleting.
                    giveInlineFeedback(0, inlineMsg);
                    checkInlineFeedback(0, inlineMsg);
                });

                it('should delete without confirmation if feedback is empty', () => {
                    giveInlineFeedback(0, inlineMsg);
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                    checkInlineFeedback(0, null);
                    // Check that adding works after deleting.
                    giveInlineFeedback(0, inlineMsg);
                    checkInlineFeedback(0, inlineMsg);
                });

                it('should delete by submitting if feedback is empty', () => {
                    giveInlineFeedback(0, inlineMsg);
                    giveInlineFeedback(0, null);
                    checkInlineFeedback(0, null);
                    // Check that adding works after deleting.
                    giveInlineFeedback(0, inlineMsg);
                    checkInlineFeedback(0, inlineMsg);
                });
            });

            context('Feedback overview', () => {
                it('should show a badge in the category if there is inline feedback', () => {
                    checkOverviewBadge(0);
                    giveInlineFeedback(0, inlineMsg);
                    checkOverviewBadge(1);
                    giveInlineFeedback(0, otherMsg);
                    checkOverviewBadge(1);
                    giveInlineFeedback(1, otherMsg);
                    checkOverviewBadge(2);
                    deleteInlineFeedback(0, null, { hasConfirm: false });
                    checkOverviewBadge(1);
                    deleteInlineFeedback(1, null, { hasConfirm: false });
                    checkOverviewBadge(0);
                });

                it('should show a message if no inline feedback is given', () => {
                    cy.openCategory('Feedback overview');
                    cy.get('.inline-feedback')
                        .should('contain', 'This submission has no line comments.');
                });

                it('should show the given inline feedback', () => {
                    giveInlineFeedback(0, inlineMsg);
                    giveInlineFeedback(1, otherMsg);

                    cy.openCategory('Feedback overview');

                    checkInlineFeedbackOverview(filename, 0, inlineMsg);
                    checkInlineFeedbackOverview(filename, 1, otherMsg);
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
                    giveInlineFeedback(0, inlineMsg, {}, selector);
                    deleteInlineFeedback(0, inlineMsg, { hasConfirm: true }, selector);
                    checkInlineFeedback(0, null, true, selector);
                });
            });
        });

        context('Single feedback viewers', () => {
            const files = {
                ImageViewer: {
                    filename: 'venn1.png',
                    outerViewer: '.image-viewer',
                    checkButtonAfterScroll: true,
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
                    checkButtonAfterScroll: true,
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
                    giveSingleFeedback(inlineMsg, opts.innerViewer);
                    getSingleFeedbackArea('non-editable', opts.innerViewer);
                    deleteSingleFeedback(opts.innerViewer);
                    checkSingleFeedback(null, false, opts.innerViewer);
                });
                reload();
                Object.values(files).forEach(opts => {
                    openFile(opts.filename, opts.outerViewer);
                    checkSingleFeedback(null, false, opts.innerViewer);
                });
            });

            it('should have a visible feedback button after scrolling down', () => {
                Object.values(files).forEach(opts => {
                    openFile(opts.filename, opts.outerViewer);
                    if (opts.checkButtonAfterScroll) {
                        scrollToBottom();
                        getSingleFeedbackButton().should('be.visible');
                    }
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

    context('Grade', () => {
        it('should be possible to give any grade between 0 and 10', () => {
            for (let grade of [0, 1.1, 2.22, 3.333, 4.5, 6/7, 8, 9.99999]) {
                giveGrade(grade);
            }
        });

        it('should not be possible to give a grade < 0 or > 10', () => {
            for (let grade of [-10, -1, -0.001, 10.001, 11, 100]) {
                giveInvalidGrade(grade, {
                    popoverMsg: 'Grade must be between 0 and 10.',
                });
            }
        });

        it('should not be possible to give an empty grade', () => {
            getGradeInput()
                .clear();
            submitGrade('error', {
                popoverMsg: 'Grade must be a number.',
            });
        });

        it('should be possible to delete the grade', () => {
            giveGrade(5);
            deleteGrade();
        });

        it('should respect the assignment\'s max grade setting', () => {
            cy.tempPatchAssignment(assignment, { max_grade: 5 }, () => {
                waitUntilLoaded();
                for (let grade of [0, 1, 5]) {
                    giveGrade(grade);
                }

                for (let grade of [-1, 6, 10]) {
                    giveInvalidGrade(grade, {
                        popoverMsg: 'Grade must be between 0 and 5.',
                    });
                }
            });

            cy.tempPatchAssignment(assignment, { max_grade: 15 }, () => {
                waitUntilLoaded();
                for (let grade of [0, 1, 10, 15]) {
                    giveGrade(grade);
                }

                for (let grade of [-1, 16, 100]) {
                    giveInvalidGrade(grade, {
                        popoverMsg: 'Grade must be between 0 and 15.',
                    });
                }
            });
        });

        it('should be visible to students when the assignment is done', () => {
            giveGrade(3.45);

            login('student1', 'Student1');
            checkGrade(null);

            cy.tempPatchAssignment(assignment, { state: 'done' }, () => {
                waitUntilLoaded();
                checkGrade(3.45);
            });
        });
    });
});
