const seed = Math.floor(Math.random() * 100000);

context('changing a permission', () => {
    let course;

    before(() => {
        cy.visit('/');
        cy.login('admin', 'admin');
        cy.createCourse(`PermissionManager Toast ${seed}`).then(res => {
            course = res;
        });
    });

    beforeEach(() => {
        cy.login('admin', 'admin');
        cy.visit(`/courses/${course.id}`);
        cy.openCategory('Permissions');
    });

    it('should show a toast with a message to reload the page', () => {
        cy.get('.permissions-manager')
            .should('be.visible')
            .find('.custom-checkbox')
            .first()
            .click();

        cy.shouldReload(() => {
            cy.get('.b-toaster')
                .contains('.toast', 'Permissions have changed')
                .should('be.visible')
                .find('.toast-body')
                .should('contain', 'Click here to reload the page and apply the changes')
                .click();
        });
    });

    it('should not show a second toast when another permission changes', () => {
        cy.reload();

        cy.get('.permissions-manager .custom-checkbox:nth(1)')
            .click();
        cy.get('.b-toaster')
            .contains('.toast', 'Permissions have changed')
            .should('have.length', 1);
        cy.get('.permissions-manager .custom-checkbox:nth(5)')
            .click();
        cy.get('.b-toaster')
            .contains('.toast', 'Permissions have changed')
            .should('have.length', 1);
    });

    it('should hide the toast when changing a permission back to its value on page load', () => {
        cy.reload();

        cy.get('.permissions-manager .custom-checkbox')
            .first()
            .click();
        cy.get('.b-toaster')
            .contains('.toast', 'Permissions have changed')
            .should('have.length', 1);
        cy.get('.permissions-manager .custom-checkbox')
            .first()
            .click();
        cy.get('.b-toaster .toast')
            .should('not.exist');
    });
});
