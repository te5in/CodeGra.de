context('Manage Assignment', () => {
    const unique = `ManageAssignment ${Math.floor(Math.random() * 10000)}`;
    let course;
    let assignment;

    before(() => {
        cy.visit('/');
        cy.createCourse(unique).then(res => {
            course = res;
            cy.createAssignment(course.id, unique).then(res => {
                assignment = res;
            });
        });
    });

    beforeEach(() => {
        cy.login('admin', 'admin');
        cy.visit(`/courses/${course.id}/assignments/${assignment.id}`);
        cy.get('.page.manage-assignment').should('exist');
    });

    context('General', () => {
        beforeEach(() => {
            cy.openCategory('General');
        });

        it('should only change then name in the header after submit was clicked', () => {
            cy.get('.page.manage-assignment')
                .find('.local-header h4.title span')
                .as('header');
            cy.get('.page.manage-assignment')
                .contains('.input-group', 'Name')
                .as('group');

            cy.get('@header').text().then((headerText) => {
                cy.get('@group').find('input').type('abc');
                cy.get('@header').text().should('not.contain', headerText + 'abc');
                cy.get('@group').find('.submit-button').submit('success');
                cy.get('@header').text().should('contain', headerText + 'abc');
            });
        });

        it('should be possible to change the state', () => {
            cy.wrap(['hidden', 'open', 'done']).each(state => {
                cy.get(`.assignment-state .state-button.state-${state}`)
                    .submit('success', {
                        hasConfirm: true,
                        waitForState: false,
                    })
                    .should('have.class', 'state-default');
            });
        });

        it('should use the correct deadline after updating it', () => {
            cy.get('.assignment-deadline')
                .click({ force: true });
            cy.get('.flatpickr-calendar .flatpickr-day:not(.prevMonthDay):not(.nextMonthDay).today')
                .click();
            cy.get('.flatpickr-calendar input.flatpickr-hour:visible')
                .clear()
                .type('23');
            cy.get('.flatpickr-calendar input.flatpickr-minute:visible')
                .clear()
                .type('59{enter}');
            cy.get('.assignment-deadline ~ .input-group-append .submit-button')
                .submit('success');
            cy.reload();

            cy.get('.local-header h4')
                .should('contain', (new Date()).toISOString().slice(0, 10))
                .should('contain', '23:59');
        });

        it('should be possible to upload a BB zip', () => {
            cy.get('.blackboard-zip-uploader').within(() => {
                cy.get('input[type=file]').uploadFixture('test_blackboard/bb.zip', 'application/zip');
                // Wait for submit button to go back to default.
                cy.get('.submit-button').submit('success');
            });
        });

        it('should be possible to set the max amount of submissions', () => {
            cy.get('.max-submissions input').type('5');
            cy.get('.max-submissions .submit-button').submit('success');
            cy.get('.max-submissions input').should('have.value', '5');

            for (let i = 0; i < 2; ++i) {
                cy.get('.submission-uploader .submission-limiting')
                    .find('.loader')
                    .should('not.exist');
                cy.get('.submission-uploader .submission-limiting')
                    .text()
                    .should('contain', '5 submissions left out of 5.');

                // Should be the same after a reload
                if (i == 0) {
                    cy.reload();
                }
            }

            cy.get('.max-submissions input').clear().type('{ctrl}{enter}');
            cy.get('.submission-uploader')
                .find('.submission-limiting')
                .should('not.exist');
            cy.get('.max-submissions input').should('have.value', '');

            cy.get('.max-submissions input').clear().type('-10');
            cy.get('.max-submissions .submit-button').submit('error', {
                popoverMsg: 'higher than or equal to 0',
            });
        });

        it('should be possible to update the cool off period', () => {
            cy.get('input.amount-in-cool-off-period').clear().type('5');
            cy.get('input.cool-off-period').clear().type('2');
            cy.get('.cool-off-period-wrapper .submit-button').submit('success');

            for (let i = 0; i < 2; ++i) {
                cy.get('.submission-uploader .submission-limiting')
                    .find('.loader')
                    .should('not.exist');
                cy.get('.submission-uploader .submission-limiting')
                    .text()
                    .should('contain', '5 times every 2 minutes');

                // Should be the same after a reload
                if (i == 0) {
                    cy.reload();
                }
            }

            cy.get('input.cool-off-period').clear().type('0{ctrl}{enter}');
            cy.get('.submission-uploader')
                .find('.submission-limiting')
                .should('not.exist');
            cy.get('input.cool-off-period').should('have.value', '0');

            cy.get('input.cool-off-period').clear().type('-1')
            cy.get('.cool-off-period-wrapper .submit-button').submit('error', {
                popoverMsg: 'higher or equal to 0',
            });

            cy.get('input.cool-off-period').clear().type('1')
            cy.get('input.amount-in-cool-off-period').clear().type('0')
            cy.get('.cool-off-period-wrapper .submit-button').submit('error', {
                popoverMsg: 'higher or equal to 1',
            });
        });

        it('should be possible to delete an assignment', () => {
            cy.get('.sidebar .sidebar-top a:nth-child(1)').click();
            cy.get('.sidebar .sidebar-top a:nth-child(2)').click();
            cy.get('.course-list').contains(course.name).click();
            cy.get('.assignment-list').should('contain', assignment.name);

            cy.get('.danger-zone-wrapper').within(() => {
                cy.get('.submit-button').contains('Delete assignment').click();
                cy.get('.modal').contains('Deleting this assignment cannot be reversed').should('be.visible')

                // Cancel should not delete
                cy.get('.submit-button').contains('Cancel').click();
                cy.get('.modal').should('not.be.visible')

                cy.get('.submit-button').contains('Delete assignment').click();
                cy.get('.submit-button').contains('Confirm').click();
            });

            cy.url().should('eq', Cypress.config().baseUrl + '/');
            cy.get('.assig-list').should('not.contain', assignment.name);
            cy.get('.course-wrapper').should('contain', course.name);

            cy.get('.sidebar .sidebar-top a:nth-child(2)').click();
            cy.get('.course-list').contains(course.name).click();
            cy.get('.assignment-list').should('not.contain', assignment.name);
        });
    });
});
