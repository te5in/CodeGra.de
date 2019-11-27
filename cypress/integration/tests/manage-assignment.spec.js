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

        it('should be possible to upload a BB zip', () => {
            cy.get('.blackboard-zip-uploader').within(() => {
                cy.get('input[type=file]').uploadFixture('test_blackboard/bb.zip', 'application/zip');
                // Wait for submit button to go back to default.
                cy.get('.submit-button').submit('success');
            });
        });
    });
});
