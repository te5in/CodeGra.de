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

    it('should be possible to create register links', () => {
        cy.openCategory('Members');
        cy.get('.users-manager .registration-link-wrapper .table').within(() => {
            cy.get('.btn[name=add-registration-link]').click();
            cy.get('tbody tr').should('have.length', 2);
            cy.get('tbody tr.registration-links').should('have.length', 1);

            // Check that by default link isn't save and doesn't have default values;
            cy.get(
                'tbody .registration-links td:nth-child(2)',
            ).contains('This link has not been saved yet');
            cy.get('.registration-links td:nth-child(3) input').should('have.value', '');
            cy.get('.registration-links .submit-button:first-child').should('be.disabled');

            cy.get('.registration-links .dropdown .btn').click();
            cy.get('.registration-links .dropdown-item').contains('Student').click();

            cy.get('.registration-links .datetime-picker').click({ force: true});
        });

        cy.get('.flatpickr-calendar .flatpickr-next-month').click();
        cy.get('.flatpickr-calendar .flatpickr-day').first().click();
        cy.get('.flatpickr-calendar .flatpickr-confirm').click();

        cy.get('.registration-links .submit-button').first().submit('success');

        cy.get('.registration-links td:nth-child(2)').contains('/register/?course_register_link_id=');
        cy.get('.registration-links td:nth-child(2)').first().find('code').then($code => {
            expect(getComputedStyle($code.get(0)).textDecoration).not.to.contain('line-through');
        });

        // It should display multiple warnings
        cy.get('.registration-links .dropdown .btn').click();
        cy.get('.registration-links .dropdown-item').contains('Teacher').click();
        cy.get('.registration-links .datetime-picker').click({ force: true});
        for (let i = 0; i < 2; ++i) {
            cy.get('.flatpickr-calendar .flatpickr-prev-month').click();
        }
        cy.get('.flatpickr-calendar .flatpickr-day').first().click();
        cy.get('.flatpickr-calendar .flatpickr-confirm').click();

        cy.get('.registration-links td:last-child .submit-button').first().submit('warning', {
            warningCallback: $el => {
                cy.wrap($el).find('li').should('have.length', 2);
                cy.wrap($el).find('li').first().contains('already expired');
                cy.wrap($el).find('li:nth-child(2)').contains('more permissions');
            },
        });
        cy.get('.registration-links td:nth-child(2)').first().find('code').then($code => {
            expect(getComputedStyle($code.get(0)).textDecoration).to.contain('line-through');
        });

        cy.get('.registration-links td:last-child .submit-button').last().submit('success', {
            hasConfirm: true,
            waitForDefault: false,
        });
        cy.get('.registration-links').should('have.length', 0);
    });
});
