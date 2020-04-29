context('No network connection', () => {
    it('Should show a toast if the server does not respond within a few seconds', () => {
        cy.visit('/');
        cy.login('admin', 'admin');

        cy.server();
        cy.route({
            method: 'GET',
            url: '/api/v1/**',
            response: '',
            status: 500,
        });

        // A request must be sent to the server, so just reload the courses.
        cy.get('.sidebar').within(() => {
            cy.get('.sidebar-entry-courses').click();
            cy.get('.submenu:last .refresh-button').click();
        });

        cy.wait(10000);
        cy.get('.toast')
            .should('contain', 'Connection error')
            .should('be.visible');
    });

    it('Should show a toast if the session has expired', () => {
        cy.visit('/');
        cy.login('admin', 'admin');

        cy.server();
        cy.route({
            method: 'GET',
            url: '/api/v1/**',
            response: '',
            status: 401,
        });

        // A request must be sent to the server, so just reload the courses.
        cy.get('.sidebar').within(() => {
            cy.get('.sidebar-entry-courses').click();
            cy.get('.submenu:last .refresh-button').click();
        });

        cy.get('.toast')
            .should('contain', 'Not logged in')
            .should('contain', 'Your session has expired')
            .should('be.visible');
    });
});
