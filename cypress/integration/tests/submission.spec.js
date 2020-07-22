context('Submission page', () => {
    const unique = Math.floor(100000 * Math.random());
    let course;
    let assignment;
    let submission;

    const generalMsg = 'General feedback message';
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
            .invoke('focus')
            .find('textarea')
            .setText(feedback)
        cy.get('@gfArea')
            .find('.submit-button')
            .submit('success');
    }

    function checkGeneralFeedbackArea(feedback) {
        cy.get('[id^="general-feedback-popover"]')
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

    function checkOverviewBadge(n) {
        if (n > 0) {
            cy.get('.categories')
                .contains('.category', 'Feedback Overview')
                .find('.badge')
                .should('contain', n.toString());
        } else {
            cy.get('.categories')
                .contains('.category', 'Feedback Overview')
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
            // Create two submissions for the same user so we have a previous
            // submission.
            cy.createSubmission(
                assignment.id,
                'test_submissions/all_filetypes.zip',
                { author: 'student1' },
            );
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
        login('admin', 'admin');
    });

    it('should be possible to reload the page on an old submission', () => {
        login('student1', 'Student1');

        // Go to previous submission.
        cy.get('.submission-nav-bar')
            .click();
        cy.get('.submission-nav-bar .dropdown-menu .dropdown-item:nth(1)')
            .click();
        // Wait for it to be loaded.
        cy.get('.file-viewer')
            .should('be.visible');
        // Reload the page.
        cy.reload();
        waitUntilLoaded();
        // There should not be an infinite loader.
        cy.get('.file-viewer')
            .should('be.visible');
        cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions/${submission.id}`);
    });

    context('General feedback', () => {
        beforeEach(() => {
            cy.openCategory('Feedback Overview');
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

        it('should show a badge in the "Feedback Overview" tab title if general feedback is not empty', () => {
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
                .find('textarea:focus')
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
                .find('textarea:focus')
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

        it('should be possible to give an empty grade', () => {
            getGradeInput().clear();
            submitGrade('success');
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
