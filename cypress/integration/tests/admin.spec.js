context('Admin page', () => {
    function getPermCheckbox(perm, role) {
        return cy.get('.permissions-manager')
            .contains('td:first-child', perm)
            .parent()
            .find(`.custom-checkbox.role-${role} input`);
    }

    context('Site permissions', () => {
        it('should be possible to change permissions', () => {
            const role = 'Admin';
            const perm = 'Create course';
            const realPerm = 'can_create_courses';

            cy.setSitePermission(realPerm, role, false);
            cy.visit('/admin');
            cy.login('admin', 'admin');
            cy.get('.permissions-manager').should('be.visible');

            getPermCheckbox(perm, role)
                .should('not.be.checked')
                .parent()
                .click();
            getPermCheckbox(perm, role)
                .should('be.checked');

            cy.reload();
            cy.get('.permissions-manager').should('be.visible');

            cy.get('.sidebar .add-course-button').should('exist');

            getPermCheckbox(perm, role)
                .should('be.checked')
                .parent()
                .click();
            getPermCheckbox(perm, role)
                .should('not.be.checked');

            cy.reload();
            cy.get('.permissions-manager').should('be.visible');

            getPermCheckbox(perm, role)
                .should('not.be.checked')

            cy.get('.sidebar .add-course-button').should('not.exist');

            cy.setSitePermission(realPerm, role, true);
        });
    });
});
