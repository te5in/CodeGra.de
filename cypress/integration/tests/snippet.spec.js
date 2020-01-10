context('Personal snippet manager', () => {
    beforeEach(() => {
        cy.visit('/');
        cy.login('admin', 'admin');
        cy.get('#global-sidebar').should('exist');
        cy.get('.sidebar-top-item.sidebar-entry-user').click();
    });

    const seed = `${Math.random()}`;
    const value = `value\n one_${seed}`;
    const key = `key_one_${seed}`;

    const getSnippet = key => {
        return cy.get('.snippet-manager tr').contains(key).parent()
    }

    it('should be possible to create a snippet', () => {
        cy.get('.snippet-manager .add-button').first().click()
        cy.get('.edit-snippet-modal .modal-title')
            .should('be.visible')
            .should('contain', 'Add snippet')

        cy.get('.edit-snippet-modal input[name=snippet-key]').type(key)
        cy.get('textarea[name=snippet-value]').type(value);
        cy.get('.edit-snippet-modal .submit-button').click()
        cy.get('.edit-snippet-modal .submit-button .label.pending').should('exist')
        cy.get('.edit-snippet-modal .submit-button .label.success').should('exist')
        cy.get('.edit-snippet-modal .modal-title').should('not.be.visible')
        cy.get('.snippet-manager td.snippet-key').should('contain', key)
        cy.get('.snippet-manager td.snippet-value').should('contain', value)
    });

    it('should not be possible to override a snippet', () => {
        cy.get('.snippet-manager .add-button').first().click()
        cy.get('.edit-snippet-modal input[name=snippet-key]').type(key)
        cy.get('textarea[name=snippet-value]').type('WOOOOOO!');
        cy.get('.edit-snippet-modal .submit-button').submit(
            'default',
            {
                hasConfirm: true,
                waitForState: false,
                doConfirm: false,
                confirmCallback: $msg => {
                    cy.wrap($msg)
                        .contains('already exists a snippet')
                        .contains(`"${value}"`);
                }
            },
        );
    })

    it('should be possible to edit a snippet', () => {
        getSnippet(key).should('contain', value)
        getSnippet(key).find('.edit-snippet-button').click()
        cy.get('.edit-snippet-modal .modal-title')
            .should('be.visible')
            .should('contain', 'Edit snippet')
        cy.get('textarea[name=snippet-value]').clear().type('NEW VALUE')
        cy.get('.edit-snippet-modal .submit-button').click()
        getSnippet(key).should('contain', 'NEW VALUE')
        getSnippet(key).should('not.contain', value)
    })

    it('should be possible to delete a snippet', () => {
        getSnippet(key).find('.delete-snippet-button')
            .click()
        cy.get('.confirm-message:visible').contains('you want to delete this')
            .parentsUntil('.popover-body').first().find('.confirm-button-accept').click()
        cy.get('.snippet-manager td.snippet-key').should('not.contain', key)
    });

    it('should not be possible to create snippets with spaces in their keys', () => {
        cy.get('.snippet-manager .add-button').first().click()
        cy.get('.edit-snippet-modal input[name=snippet-key]').type(key + ' woo')
        cy.get('textarea[name=snippet-value]').type(value);
        cy.get('.edit-snippet-modal .submit-button').click()
        cy.get('.edit-snippet-modal .submit-button .label.pending').should('exist')
        cy.get('.edit-snippet-modal .submit-button .label.error').should('exist')
        cy.get('.popover-body').should('contain', 'Snippet names may not contain spaces')
    })
});
