context('Register', () => {
    beforeEach(() => {
        cy.visit('/');
        cy.logout();
        cy.visit('/register');
    });

    function getUsername() {
        return `test-student-${Math.floor(Math.random() * 100000)}`;
    }

    function getPassword() {
        return 'f941f3ab-0fa5-4c21-bea8-fd626ac0a821';
    }

    function fillField(field, value) {
        cy.get('fieldset.form-group')
            .contains('.input-group', field)
            .find('input')
            .type(value);
    }

    function submit(state, opts = {}) {
        cy.get('.submit-button').submit(state, Object.assign(opts, {
            // We never wait for the default state, because after login the
            // submit button will disappear instantly.
            waitForDefault: false,
            hasConfirm: true,
        }));
    }

    it('should successfully register a user if all fields are filled in', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('success');
    });

    it('should show an error if the username is not passed', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'Field "Username" is empty' });
    });

    it('should show an error if the full name is not passed', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'Field "Full name" is empty' });
    });

    it('should show an error if the email is not passed', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'Field "Email" is empty' });
    });

    it('should show an error if the repeat email is not passed', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'Field "Repeat email" is empty' });
    });

    it('should show an error if the password is not passed', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'Field "Password" is empty' });
    });

    it('should show an error if the repeat password is not passed', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);

        submit('error', { popoverMsg: 'Field "Repeat password" is empty' });
    });

    it('should show an error if the emails are different', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email2@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'The emails do not match' });
    });

    it('should show an error if the passwords are different', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', 'asdf');

        submit('error', { popoverMsg: 'The passwords do not match' });
    });

    it('should show an error if the user already exists', () => {
        const username = getUsername();
        const password = getPassword();

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('success');

        cy.logout();
        cy.visit('/register');

        fillField('Username', username);
        fillField('Full name', username);
        fillField('Email', 'email@example.com');
        fillField('Repeat email', 'email@example.com');
        fillField('Password', password);
        fillField('Repeat password', password);

        submit('error', { popoverMsg: 'The given username is already in use' });
    });
});
