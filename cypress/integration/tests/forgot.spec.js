context('Forgot password', () => {
    beforeEach(() => {
        cy.visit('/forgot');
    });

    it('should succeed when the user exists', () => {
        cy.server();
        cy.route('PATCH', '/api/v1/login?type=reset_email')
            .as('forgotRequest');

        cy.get('input[name="username"]').type('robin');
        cy.get('.submit-button').click();

        cy.wait('@forgotRequest');
    });

    it('should work with enter', () => {
        cy.server();
        cy.route('PATCH', '/api/v1/login?type=reset_email')
            .as('forgotRequest');

        cy.get('input[name="username"]').type('robin{enter}');

        cy.wait('@forgotRequest');
    });

    it('should show an error when no username is given', () => {
        cy.get('.submit-button').submit('error');
    });

    it('should show an error when the user does not exist', () => {
        cy.get('input[name="username"]').type('asdfasdf');
        cy.get('.submit-button').submit('error');
    });

    it('should have a link to the login page', () => {
        cy.get('a[href*="login"]')
            .should('contain', 'Login')
            .and('be.visible')
            .click();
        cy.get('.page.login').should('be.visible');
    });
});
