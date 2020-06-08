context('General messages', () => {
    // It is not possible to stub a "no response" in Cypress, so we can't
    // really test this.
    it.skip('Should show a toast if the server does not respond within a few seconds', () => {
        cy.visit('/');
        cy.login('admin', 'admin');

        cy.server();
        cy.route({
            method: 'GET',
            url: '/api/v1/**',
            response: '',
            status: 0,
        });

        // A request must be sent to the server, so just reload the courses.
        cy.get('.sidebar').within(() => {
            cy.get('.sidebar-entry-courses').click();
            cy.get('.submenu:last .refresh-button').click();
        });

        cy.wait(10000);
        cy.get('.toast')
            .should('contain', 'Unknown error')
            .should('be.visible');
    });

    it('should show a toast if the response code is a 5xx', () => {
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
            .should('contain', 'Unknown error')
            .should('be.visible');
    });

    it('should show the same toast for a second time, after it has been closed', () => {
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
            .should('contain', 'Unknown error')
            .should('be.visible')
            .find('.close')
            .click();

        // A request must be sent to the server, so just reload the courses.
        cy.get('.sidebar').within(() => {
            cy.get('.sidebar-entry-courses').click();
            cy.get('.submenu:last .refresh-button').click();
        });

        cy.wait(10000);
        cy.get('.toast')
            .should('contain', 'Unknown error')
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

    it('should show a toast if the jwt token is invalid', () => {
        cy.visit('/');
        cy.login('admin', 'admin');

        cy.window().then($window => {
            $window.__app__.$store.state.user.jwtToken = 'xxx';
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

    it('should show a toast if a non logged-in user requests a resource that needs authorization', () => {
        cy.visit('/');
        cy.login('admin', 'admin');

        cy.window().then($window => {
            $window.__app__.$store.state.user.jwtToken = null;
        });

        // A request must be sent to the server, so just reload the courses.
        cy.get('.sidebar').within(() => {
            cy.get('.sidebar-entry-courses').click();
            cy.get('.submenu:last .refresh-button').click();
        });

        cy.get('.toast')
            .should('contain', 'Not logged in')
            .should('contain', 'You are currently not logged in.')
            .should('be.visible');
    });
});
