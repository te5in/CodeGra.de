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
import moment from 'moment';

Cypress.Commands.add('getAll', (aliases) => {
    // Get the value for multiple aliases at once.

    const values = [];

    cy.wrap(aliases).each(alias => {
        return cy.get(alias).then(value => values.push(value));
    }).then(() => {
        return values;
    });
});

Cypress.Commands.add('text', { prevSubject: true }, subject => {
    // Get the text in an element, with all consecutive whitespace replaced
    // with a single space. Returns a cy wrapper so it can be used in an async
    // context.
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

function getAuthHeaders() {
    return cy.window().its('__app__').then(app => {
        const { jwtToken } = app.$store.state.user;
        return { Authorization: `Bearer ${jwtToken}` };
    });
}

Cypress.Commands.add('authRequest', (options) => {
    // Do a request as the logged in user.

    return getAuthHeaders().then(headers => {
        options.headers = Object.assign(options.headers || {}, headers);
        return cy.request(options);
    });
});

Cypress.Commands.add('formRequest', (options) => {
    // Send a request with a FormData object as body.  This is impossible with
    // cy.request, and must be used to send requests to the server containing
    // files. Use cy.fixtureAsFile to load a fixture as a File object suitable
    // to be used in FormData. The request is sent as the logged in user.

    let { url, method, headers, data } = options;

    return getAuthHeaders().then(authHeaders => {
        headers = Object.assign(headers || {}, authHeaders)
        return cy
            .server()
            .route(method, url)
            .as('formRequest')
            .window()
            .then(win => {
                var xhr = new win.XMLHttpRequest();
                xhr.open(method, url);
                Object.entries(headers).forEach(([name, value]) => {
                    xhr.setRequestHeader(name, value);
                });
                xhr.send(data);
            })
            .wait('@formRequest');
    });
});

Cypress.Commands.add('fixtureAsFile', (path, filename, mimeType) => {
    // Load a fixture and return it as a File object.

    return cy.fixture(path, 'base64').then(fixture => {
        const decoded = atob(fixture);
        const len = decoded.length;
        const u8arr = new Uint8Array(len);

        for (let i = 0; i < len; i++) {
            u8arr[i] = decoded.charCodeAt(i);
        }

        return cy.wrap(new File([u8arr], filename, { type: mimeType }));
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

Cypress.Commands.add('createCourse', (name, users=[]) => {
    cy.login('admin', 'admin');

    return cy.authRequest({
        url: '/api/v1/courses/',
        method: 'POST',
        body: { name },
    }).its('body').then(course => {
        // Get the course roles so we can map a role name
        // to a role id.
        return cy.authRequest({
            url: `/api/v1/courses/${course.id}/roles/`,
            method: 'GET',
        }).its('body').then(roles => {
            return [course, roles];
        });
    }).then(([course, roles]) => {
        // Register each user for the course.
        cy.wrap(users).each(user => {
            const role = roles.find(r => r.name == user.role);
            cy.authRequest({
                url: `/api/v1/courses/${course.id}/users/`,
                method: 'PUT',
                body: {
                    username: user.name,
                    role_id: role.id,
                },
            });
        })
        cy.log('created course', course);
        return cy.wrap(course);
    });
});

Cypress.Commands.add('createAssignment', (courseId, name, { state, bbZip, deadline } = {}) => {
    cy.login('admin', 'admin');

    cy.authRequest({
        url: `/api/v1/courses/${courseId}/assignments/`,
        method: 'POST',
        body: { name },
    }).its('body').then(assignment => {
        const body = {};

        if (state !== undefined) {
            body.state = state;
        }

        if (deadline !== undefined) {
            if (deadline === 'tomorrow') {
                deadline = moment().add(1, 'day').endOf('day');
                deadline = deadline.toISOString();
            }
            body.deadline = deadline;
        }

        if (Object.keys(body).length > 0) {
            cy.authRequest({
                url: `/api/v1/assignments/${assignment.id}`,
                method: 'PATCH',
                body,
            });
        }

        if (bbZip) {
            cy.fixtureAsFile('test_blackboard/bb.zip', 'bb.zip', 'application/zip').then(bbZipFile => {
                const data = new FormData();
                data.append('file', bbZipFile);

                return cy.formRequest({
                    url: `/api/v1/assignments/${assignment.id}/submissions/`,
                    method: 'POST',
                    data,
                });
            });
        }

        cy.log('created assignment', assignment);
        return cy.wrap(assignment);
    });
});

Cypress.Commands.add('createRubric', (assignmentId, rubricData, maxPoints = null) => {
    return cy.authRequest({
        url: `/api/v1/assignments/${assignmentId}/rubrics/`,
        method: 'PUT',
        body: {
            rows: rubricData,
            max_points: maxPoints,
        },
    });
});

Cypress.Commands.add('openCategory', (name) => {
    cy.get('.local-header').contains('.category', name).click();
});

// Upload a fixture to a file input.
Cypress.Commands.add('uploadFixture', { prevSubject: true }, (subject, fileName, mimeType = 'application/octet-stream') => {
    // Ensure this is a file input.
    cy.wrap(subject).should('have.prop', 'tagName').should('eq', 'INPUT');
    cy.wrap(subject).should('have.prop', 'type').should('eq', 'file');

    return cy.fixture(fileName).then(fileContent => {
        return cy.wrap(subject).upload({ fileContent, fileName, mimeType });
    });
});

// Click a submit button, and optionally wait for its state to return back to
// default.
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

Cypress.Commands.add('multiselect', { prevSubject: true }, (subject, items) => {
    // Select items in a <multiselect>. Each item is typed in the multiselect
    // and then the first matching item is selected. Fails if no matching items
    // could be found.

    cy.wrap(items).each(item => {
        cy.wrap(subject)
            .should('have.class', 'multiselect')
            .find('input')
            .type(item);
        cy.wrap(subject)
            .find('.multiselect__element')
            .first()
            .click();
    });
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
