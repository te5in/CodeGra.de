// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
import 'cypress-file-upload';

// Get the text in an element, with all consecutive whitespace replaced with a
// single space. Returns a cy wrapper so it can be used in an async context.
Cypress.Commands.add('text', { prevSubject: true }, subject => {
    return subject.text().replace(/\s+/g, ' ');
});

Cypress.Commands.add('login', (username, password, force=true) => {
    return cy.request({
        url:'/api/v1/login',
        method: 'POST',
        body: {
            username,
            password,
        }
    }).its('body').then(body => {
        cy.window().its('__app__').then(app => {
            const url = app.$router.getRestoreRoute();
            app.$store.dispatch('user/login', { data: body });
            if (url) {
                cy.visit(url.fullPath);
            } else {
                cy.reload()
            }
        });
    });
});

Cypress.Commands.add('logout', () => {
    cy.window().its('__app__').then(app => {
        app.$store.dispatch('user/logout');
        cy.visit('/');
    });
});

Cypress.Commands.add('setSitePermission', (perm, role, value) => {
    let reload = false;

    cy.login('admin', 'admin');
    cy.visit('/admin');

    cy.get('.permissions-table')
        .contains('tr', perm)
        .find(`.custom-checkbox.role-${role}`)
        .parent()
        .as('container');
    cy.get('@container')
        .find(`.custom-checkbox.role-${role}`)
        .as('check');

    // If the input does not have the correct value,
    cy.get('@container')
        .find(`input`)
        .then($input => {
            if ($input.get(0).checked != value) {
                cy.get('@check').click();
                reload = true;
                cy.get('@container').find('.loader');
                cy.get('@container').find('input');
            }
        });
    cy.get('@container')
        .find('input')
        .should(value ? 'be.checked' : 'not.be.checked')
        .then(() => {
            if (reload) {
                cy.reload();
            }
        });
});

Cypress.Commands.add('createUser', (username, password, email = `${username}@example.com`) => {
    return cy.request({
        url: '/api/v1/user',
        method: 'POST',
        body: { name: username, username, password, email },
    });
});

Cypress.Commands.add('createCourse', (name, users) => {
    cy.login('admin', 'admin');
    cy.visit('/admin');

    // Make sure we have the "Create course" permission.
    cy.setSitePermission('Create course', 'Admin', true);

    cy.get('.sidebar .add-course-button').click();
    cy.get('.popover .submit-input input').type(name);
    cy.get('.popover .submit-input .btn').click();

    // Wait for manage-course page to be loaded.
    cy.get('.page.manage-course').should('exist');

    cy.get('.users-manager').within(() => {
        users.forEach(user => {
            cy.get('.user-selector input').type(user.name);
            // Input is emptied when the multiselect is unfocused, so click
            // the entry.
            cy.get('.user-selector .multiselect__element').click();
            cy.get('.add-student .dropdown .btn').click();
            cy.get('.add-student .dropdown-item').contains(user.role).click();

            // Wait for submit button to go back to default.
            cy.get('.add-student .submit-button').submit('success');
        });
    });
});

Cypress.Commands.add('createAssignment', (name, { state, bbZip } = {}) => {
    // Assumes the assignment list of the course that the assignment should be
    // added to is visible in the sidebar.

    cy.get('.sidebar .add-assignment-button').click();
    cy.get('.popover .submit-input input').type(name);
    cy.get('.popover .submit-input .btn').click();

    // Wait for manage-assignment page to be loaded.
    cy.get('.page.manage-assignment .local-header').should('contain', name);

    if (state) {
        cy.get(`.assignment-state .state-button.state-${state}`)
            .submit('success', {
                hasConfirm: true,
                waitForState: false,
            })
            .should('have.class', 'state-default');
    }

    if (bbZip) {
        cy.get('.blackboard-zip-uploader').within(() => {
            cy.get('input[type=file]').uploadFixture('test_blackboard/bb.zip', 'application/zip');
            // Wait for submit button to go back to default.
            cy.get('.submit-button').submit('success');
        });
    }
});

Cypress.Commands.add('uploadFixture', { prevSubject: true }, (subject, fileName, mimeType = 'application/octet-stream') => {
    // Ensure this is a file input.
    cy.wrap(subject).should('have.prop', 'tagName').should('eq', 'INPUT');
    cy.wrap(subject).should('have.prop', 'type').should('eq', 'file');

    return cy.fixture(fileName).then(fileContent => {
        return cy.wrap(subject).upload({ fileContent, fileName, mimeType });
    });
});

Cypress.Commands.add('submit', { prevSubject: true }, (subject, state, optsArg = {}) => {
    const opts = Object.assign({
        popoverMsg: '',
        hasConfirm: false,
        doConfirm: true,
        waitForState: true,
        waitForDefault: true,
    }, optsArg);

    // Ensure this is a submit button.
    cy.wrap(subject).should('have.class', 'submit-button');
    cy.wrap(subject).click();

    // Click a button the confirm popover.
    if (opts.hasConfirm) {
        cy.get('.popover .submit-button-confirm')
            .contains('.btn', opts.doConfirm ? 'Yes' : 'No')
            .click();
    }

    if (!opts.waitForState) {
        return cy.wrap(subject);
    }

    cy.wrap(subject).should('have.class', `state-${state}`);

    // Close the error/warning popover.
    if (state === 'error' || state == 'warning') {
        cy.get(`.popover .submit-button-${state}`)
            .should('contain', opts.popoverMsg)
            .find('.hide-button')
            .click();
    }

    if (opts.waitForDefault) {
        cy.wrap(subject).should('have.class', 'state-default');
    }

    return cy.wrap(subject);
});
//
//
// -- This is a child command --
// Cypress.Commands.add("drag", { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add("dismiss", { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This is will overwrite an existing command --
// Cypress.Commands.overwrite("visit", (originalFn, url, options) => { ... })

// Cypress.Commands.add('url', 'http://localhost:8080')
