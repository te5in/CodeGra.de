context('Login', () => {
    const username = `test-student-${Math.floor(Math.random() * 100000)}`;
    const password = 'f941f3ab-0fa5-4c21-bea8-fd626ac0a821';

    // Create a user with a strong password so we don't get the password
    // warning popovers on each login.
    before(() => {
        cy.visit('/');
        cy.createUser(username, password);
    });

    beforeEach(() => {
        cy.visit('/');
        cy.logout();
    });

    function fillUser(user) {
        cy.get('input[type="text"]').type(user);
    }

    function fillPw(pw) {
        cy.get('input[type="password"]').type(pw);
    }

    function fillBoth(user, pw) {
        fillUser(user);
        fillPw(pw);
    }

    function submit(state, opts = {}) {
        cy.get('.submit-button').submit(state, Object.assign(opts, {
            // If we succesfully log in, the button will never be in the success
            // state because it is removed from the page before the state gets
            // set.
            waitForState: state !== 'success',
            // We never wait for the default state, because after login the
            // submit button will disappear instantly.
            waitForDefault: false,
        }));
    }

    it('login successful', () => {
        fillBoth(username, password);
        submit('success');

        cy.url().should('eq', Cypress.config().baseUrl + '/');

        cy.get('.sidebar-top-item.sidebar-entry:first').click();
        cy.get('.sidebar-user-info .userinfo input[type=text][name=full-name]')
            .should('be.visible')
            .and('have.value', username);
        cy.get('.sidebar-user-info .snippets .snippet-manager').should('exist');
    })

    it('should work with enter in password', () => {
        fillBoth(username, `${password}{enter}`);

        cy.url().should('eq', Cypress.config().baseUrl + '/');
    });

    it('should work with enter in username', () => {
        fillPw(`${password}{backspace}${password[password.length - 1]}`);
        fillUser(`${username}{enter}`);

        cy.url().should('eq', Cypress.config().baseUrl + '/');
    });

    it('should show a warning when the password is too easy', () => {
        fillBoth('robin', 'Robin');
        submit('warning', {
            popoverMsg: 'Your password does not meet the requirements, consider changing it',
        });
    });

    it('should show an error when no username is given', () => {
        fillPw(password);
        submit('error', { popoverMsg: 'Please enter a username' });
    })

    it('should show an error when no password is given', () => {
        fillUser(username);
        submit('error', { popoverMsg: 'Please enter a username and password' });
    })

    it('should show an error when wrong password is given', () => {
        fillBoth(username, 'INCORRECT_PASSWORD');
        submit('error', { popoverMsg: 'The supplied username or password is wrong' });
    })

    it('should have a link to the forgot password page', () => {
        cy.get('a[href*="forgot"]')
            .should('contain', 'Forgot')
            .and('be.visible')
            .click();
        cy.get('.page.forgot-password').should('be.visible');
    });
});
