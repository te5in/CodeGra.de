context('Analytics Dashboard', () => {
    let unique = Math.floor(Math.random() * 100000);
    let course;
    let assignment;
    let assignmentNoRubric;
    let assignmentNoSubs;

    function loadPage(assig) {
        cy.visit(`/courses/${course.id}/assignments/${assig.id}/submissions#analytics`);
        cy.url().should('include', `assignments/${assig.id}`);
        cy.get('.analytics-dashboard')
            .should('be.visible')
            .find('.analytics-general-stats')
            .should('be.visible');
    }

    before(() => {
        cy.createCourse(
            `Analytics dashboard ${unique}`,
            [
                { name: 'student1', role: 'Student' },
                { name: 'student2', role: 'Student' },
                { name: 'student3', role: 'Student' },
                { name: 'student4', role: 'Student' },
            ],
        ).then(res => {
            course = res;
            return cy.createAssignment(
                course.id,
                `Analytics Dashboard ${unique}`,
                { state: 'open', deadline: 'tomorrow' },
            );
        }).then(res => {
            assignment = res;
            return cy.createAssignment(
                course.id,
                `Analytics Dashboard ${unique} (No Rubric)`,
                { state: 'open', deadline: 'tomorrow' },
            );
        }).then(res => {
            assignmentNoRubric = res;
            return cy.createAssignment(
                course.id,
                `Analytics Dashboard ${unique} (No Submissions)`,
                { state: 'open', deadline: 'tomorrow' },
            );
        }).then(res => {
            assignmentNoSubs = res;
            return cy.fixture('test_rubrics/long_description.json');
        }).then(res => {
            return cy.createRubric(assignment.id, res);
        }).then(() => {
            return cy.wrap([
                'student1',
                'student2',
                'student3',
                'student4',
            ]).each(author => {
                return cy.wrap([
                    assignment,
                    assignmentNoRubric,
                ]).each(assig => {
                    return cy.createSubmission(
                        assig.id,
                        'test_submissions/all_filetypes.zip',
                        { author },
                    );
                });
            });
        });
        cy.visit('/');
    });

    context('as a teacher', () => {
        beforeEach(() => {
            cy.login('admin', 'admin');
            loadPage(assignment);
        });

        it('should show the general statistics', () => {
            cy.get('.analytics-general-stats')
                .should('be.visible')
                .within(() => {
                    cy.get('.card-body')
                        .contains('.metric', 'Students')
                        .should('contain', '4');
                    cy.get('.card-body')
                        .contains('.metric', 'Submissions')
                        .should('contain', '4');
                    cy.get('.card-body')
                        .contains('.metric', 'Average grade')
                        .should('contain', '-');
                    cy.get('.card-body')
                        .contains('.metric', 'Average submissions')
                        .should('contain', '1');
                    cy.get('.card-body')
                        .contains('.metric', 'Average inline feedback')
                        .should('contain', '0');
                });
        });

        it('should not clutter the URL with lots of settings', () => {
            function myEncodeURI(str) {
                // Vue router encodes colons, while encodeURI does not...
                return encodeURI(str).replace(/:/g, '%3A');
            }

            cy.url().should('contain', `analytics=${myEncodeURI('{}')}`);
            cy.get('.analytics-filters')
                .contains('.btn', 'Add filter')
                .click();
            cy.get('.analytics-filters .filter')
                .should('have.length', 2);
            cy.url().should('contain', `analytics=${myEncodeURI('{"filters":[{},{}]}')}`);
            cy.get('.analytics-filters')
        });

        context('Filters', () => {
            it('should be possible to duplicate a filter', () => {
                cy.get('.analytics-filters .filter:nth(0)')
                    .contains('.input-group', 'Min. grade')
                    .find('input')
                    .setText('5');
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .find('.icon-button.clone')
                    .click();
                cy.get('.analytics-filters .filter')
                    .should('have.length', 2)
                    .each($filter => {
                        cy.wrap($filter)
                            .contains('.input-group', 'Min. grade')
                            .find('input')
                            .should('have.value', '5');
                    });
            });

            it('should be possible to split a filter', () => {
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .eq(0)
                    .as('filter');
                cy.get('@filter')
                    .find('.icon-button.split')
                    .click()
                    .should('have.class', 'active');
                cy.get('@filter')
                    .contains('.split-controls .input-group', 'Grade')
                    .find('input')
                    .setText('5');
                cy.get('@filter')
                    .find('.submit-button')
                    .submit('success');
                cy.get('.analytics-filters .filter')
                    .should('have.length', 2);
            });

            it('should show stats for each filter resulting from a split', () => {
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .eq(0)
                    .as('filter');
                cy.get('@filter')
                    .find('.icon-button.split')
                    .click()
                    .should('have.class', 'active');
                cy.get('@filter')
                    .find('.split-controls .analytics-general-stats')
                    .should('have.length', 1);
                cy.get('@filter')
                    .contains('.split-controls .input-group', 'Grade')
                    .find('input')
                    .setText('5');
                cy.get('@filter')
                    .find('.split-controls .analytics-general-stats')
                    .should('have.length', 2);
                cy.get('@filter')
                    .contains('.split-controls .input-group', 'Latest')
                    .find('label')
                    .click();
                cy.get('@filter')
                    .find('.split-controls .analytics-general-stats')
                    .should('have.length', 4);
                cy.get('@filter')
                    .contains('.split-controls .input-group', 'Latest')
                    .find('label')
                    .click();
                cy.get('@filter')
                    .find('.split-controls .analytics-general-stats')
                    .should('have.length', 2);
            });

            it('should be possible to delete a filter', () => {
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .find('.icon-button.clone')
                    .click();
                cy.get('.analytics-filters .filter')
                    .should('have.length', 2)
                    .eq(1)
                    .find('.icon-button.delete')
                    .click();
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1);
            });

            it('should not be possible to delete the last filter', () => {
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .find('.icon-button.delete')
                    .should('have.class', 'text-muted')
                    .click();
                cy.wait(200);
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1);
            });

            it('should be possible to reset the filters', () => {
                cy.get('.analytics-filters .filter:nth(0)')
                    .contains('.input-group', 'Min. grade')
                    .find('input')
                    .setText('5');
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .find('.icon-button.clone')
                    .click();
                cy.get('.analytics-filters .filter')
                    .should('have.length', 2)
                    .eq(1)
                    .contains('.custom-checkbox:first label', 'Only use latest submissions')
                    .click();
                cy.get('.analytics-filters .icon-button.reset')
                    .click();
                cy.get('.analytics-filters .filter')
                    .should('have.length', 1)
                    .contains('.input-group', 'Min. grade')
                    .find('input')
                    .should('have.value', '');
            });
        });

        context('Submission date histogram', () => {
            it('should be visible', () => {
                cy.get('.analytics-submission-date')
                    .should('be.visible');
            });

            it('should be visible when there are no submissions', () => {
            });
        });

        context('Submission count histogram', () => {
            it('should be visible', () => {
                cy.get('.analytics-submission-date')
                    .should('be.visible');
            });

            it('should be visible when there are no submissions', () => {
            });
        });

        context('Grade histogram', () => {
            it('should be visible', () => {
                cy.get('.analytics-grade-stats')
                    .should('be.visible');
            });

            it('should be visible when there are no submissions', () => {
            });
        });

        context('Rubric statistics', () => {
            it('should be visible', () => {
                cy.get('.analytics-rubric-stats')
                    .should('be.visible');
            });

            it('should be visible when there are no submissions', () => {
            });
        });
    });

    context('as a student', () => {
        beforeEach(() => {
            cy.login('student1', 'Student1');
            cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions#analytics`);
            cy.get('.analytics-dashboard')
                .should('be.visible')
                .find('.loader')
                .should('not.exist');
        });

        it('should not be possible to access the analytics dashboard', () => {
            cy.get('.analytics-dashboard .alert-danger')
                .should('be.visible')
                .should('contain', 'You do not have permission to view the Analytics Dashboard');
        });
    });
});
