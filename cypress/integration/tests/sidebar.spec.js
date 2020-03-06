context('Sidebar', () => {
    before(() => {
        cy.visit('/');
    });

    it('should be possible to create a course', () => {
        const course = `Course ${Math.floor(Math.random() * 10000)}`;

        cy.login('admin', 'admin');

        // Make sure we have the "Create course" permission.
        cy.setSitePermission('can_create_courses', 'Admin', true);
        cy.visit('/');

        cy.get('.sidebar .sidebar-entry-courses').click();
        cy.get('.sidebar .add-course-button').should('be.visible').click();
        cy.get('#add-course-popover')
            .should('not.have.class', 'fade')
            .within(() => {
                cy.get('input').type(course);
                cy.get('.submit-button').click();
            });

        // Wait for manage-course page to be loaded.
        cy.get('.page.manage-course').should('exist');
        cy.get('.sidebar .submenu-header').should('contain', course);
    });

    it('should be possible to create an assignment', () => {
        const assig = `Assignment ${Math.floor(Math.random() * 10000)}`;

        cy.login('admin', 'admin');
        cy.createCourse(assig).then(course => {
            cy.visit(`/courses/${course.id}`);
        });

        cy.get('.sidebar .add-assignment-button').should('be.visible').click();
        cy.get('#add-assignment-popover')
            .should('not.have.class', 'fade')
            .within(() => {
                cy.get('input').type(assig);
                cy.get('.submit-button').click();
            });

        // Wait for manage-assignment page to be loaded.
        cy.get('.page.manage-assignment').should('exist');
        cy.get('.local-header').should('contain', assig);
    });

    context('Profile page', () => {
        function openProfile() {
            return cy.get('.sidebar-top-item.sidebar-entry-user').click()
        }

        function getSubmit() {
            return cy.get('.submit-button[name=submit-user-info]');
        }

        it('should be possible to change your name', () => {
            const oldName = 'admin';
            const newName = `HAHA A NAME: ${Math.floor(Math.random() * 10000)}`;

            cy.login('admin', 'admin');

            cy.visit('/');
            openProfile();
            cy.get('input[name=full-name]').clear()
            getSubmit().submit('error', {
                popoverMsg: 'Your new name cannot be empty'
            });
            cy.get('.sidebar-top-item.sidebar-entry-user .name').text().should('eq', oldName);
            cy.get('input[name=full-name]').type(newName);
            getSubmit().submit('success');
            cy.get('.sidebar-top-item.sidebar-entry-user .name').contains(newName);

            cy.reload();
            cy.get('.sidebar-top-item.sidebar-entry-user .name').text().should('eq', newName);
            openProfile();

            cy.get('input[name=full-name]').clear().type(oldName);
            getSubmit().submit('success');
            cy.get('.sidebar-top-item.sidebar-entry-user .name').text().should('eq', oldName);
        });

        it('should be possible to change your email', () => {
            const oldEmail = 'admin@example.com';
            const incorrectEmail = 'admin@example';
            const newEmail = `admina-${Math.random()}@example.nl`;

            function submitEmail(email, password) {
                cy.get('input[name=email]').clear()
                if (email) {
                    cy.get('input[name=email]').type(email)
                }

                cy.get('.password-input input[name=old-password]').clear();
                if (password) {
                    cy.get('.password-input input[name=old-password]').type(password);
                }
                return getSubmit();
            }

            cy.login('admin', 'admin');
            openProfile();
            cy.get('input[name=email]').should('have.value', oldEmail);

            submitEmail('', '').submit('error', { popoverMsg: 'not valid' });
            submitEmail(incorrectEmail, '').submit('error', { popoverMsg: 'not valid' });
            submitEmail(newEmail, '').submit('error', { popoverMsg: 'need a correct old password' });
            submitEmail(newEmail, 'incorrect pass').submit('error', { popoverMsg: 'given old password is wrong' });
            submitEmail(newEmail, 'admin').submit('success');

            cy.reload();
            openProfile();
            cy.get('input[name=email]').should('have.value', newEmail);
            submitEmail(oldEmail, 'admin').submit('success');
        });

        it('should be possible to reset the fields', () => {
            cy.login('admin', 'admin');
            openProfile();
            let inputs = [];
            cy.get('.userinfo').find('input').each($el => {
                inputs.push($el.val());
            });
            cy.log(inputs);

            cy.get('.userinfo').find('input').each(($el, $index) => {
                if ($index > 0) {
                    cy.wrap($el).clear().type(`HELLO! - ${Math.random()}`);
                }
            });

            cy.get('.userinfo .btn.btn-danger').click();
            cy.get('.userinfo').find('input').each(($el, $index) => {
                cy.wrap($el).should('have.value', inputs[$index]);
            });
        });

        it('should be possible to toggle between dark and light mode', () => {
            cy.login('admin', 'admin');
            openProfile();

            cy.get('body').should('not.have.class', 'cg-dark-mode');
            cy.get('.settings-content .toggle-container.colors').should('exist');
            cy.get('.settings-content .toggle-container.colors[checked=checked]').should('not.exist');

            cy.get('.settings-content .toggle-container .label-on').click();
            cy.get('body').should('have.class', 'cg-dark-mode');

            cy.reload();
            cy.get('body').should('have.class', 'cg-dark-mode');
            openProfile();
            cy.get('.settings-content .toggle-container.colors[checked=checked]').should('exist');
            cy.get('.settings-content .toggle-container .toggle').click();
            cy.get('body').should('not.have.class', 'cg-dark-mode');
        });
    });
});
