context('Manage Course', () => {
    const uniqueName = `ManageCourse ${Math.floor(Math.random() * 100000)}`;
    let course;

    before(() => {
        cy.visit('/');
        cy.login('admin', 'admin');
        cy.createCourse(uniqueName).then(res => {
            course = res;
        });
    });

    beforeEach(() => {
        cy.login('admin', 'admin');
        cy.visit(`/courses/${course.id}`);
    });

    it('should be possible to add users to the course', () => {
        const users = [
            { name: 'Robin', role: 'Teacher' },
            { name: 'Student1', role: 'TA' },
            { name: 'Student2', role: 'Student' },
            { name: 'Student3', role: 'Designer' },
            { name: 'Student4', role: 'Observer' },
        ];

        cy.openCategory('Members');

        cy.get('.users-manager').within(() => {
            cy.wrap(users).each(user => {
                cy.get('.user-selector input').type(user.name);
                // Input is emptied when the multiselect is unfocused, so click
                // the entry.
                cy.get('.user-selector .multiselect__element').click();
                cy.get('.add-student .dropdown .btn').click();
                cy.get('.add-student .dropdown-item').contains(user.role).click();

                // Wait for submit button to go back to default.
                cy.get('.add-student .submit-button').submit('success');
                cy.get('table')
                    .contains('tr', user.name)
                    .should('contain', user.role);
            });
        });
    });
});
