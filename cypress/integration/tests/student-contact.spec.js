context('StudentContact', () => {
    const seed = Math.floor(Math.random() * 100000);
    let course;
    let assignment;

    before(() => {
        cy.createCourse(
            `Student Contact ${seed}`,
            [
                { name: 'student1', role: 'Student' },
            ],
        ).then(res => {
            course = res;
            return cy.createAssignment(
                course.id,
                `Student Contact ${seed}`,
                { state: 'open', deadline: 'tomorrow' },
            );
        }).then(res => {
            assignment = res;
            return Cypress.Promise.all([
                cy.createSubmission(
                    assignment.id,
                    'test_submissions/all_filetypes.zip',
                    { author: 'student1' },
                ),
                cy.createSubmission(
                    assignment.id,
                    'test_submissions/all_filetypes.zip',
                    { testSub: true },
                ),
            ]);
        });
        cy.visit('/');
    });

    it('should not be possible on the submission page of a test student', () => {
        cy.login('admin', 'admin');
        cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions/`);
        cy.get('.submission-list')
            .contains('tr', 'Test Student')
            .click();
        cy.get('#codeviewer-email-students')
            .should('not.exist');
    });

    it('should not include the test student on the submissions page', () => {
        cy.login(
            'admin',
            'admin',
            `/courses/${course.id}/assignments/${assignment.id}/submissions/`,
        );
        cy.get('#submissions-page-email-students-button')
            .click();
        cy.get('#submissions-page-email-students-modal .user-selector .multiselect')
            .should('not.contain', 'Test Student');
    });
});
