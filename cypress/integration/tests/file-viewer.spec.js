context('FileViewer', () => {
    const uniqueName = `FileViewer ${Math.floor(Math.random() * 100000)}`;
    let course;
    let assignment;
    let submissionURL;

    before(() => {
        cy.visit('/');

        cy.createCourse(uniqueName, [
            { name: 'student1', role: 'Student' },
        ]).then(res => {
            course = res;

            return cy.createAssignment(course.id, uniqueName, {
                state: 'open',
                deadline: 'tomorrow',
            })
        }).then(res => {
            assignment = res;
            return cy.createSubmission(
                assignment.id,
                'test_submissions/all_filetypes.zip',
                { author: 'student1' },
            );
        }).then(res => {
            submissionURL = `/courses/${course.id}/assignments/${assignment.id}/submissions/${res.id}`;
        });
    });

    beforeEach(() => {
        cy.login('admin', 'admin');
        cy.visit(submissionURL);
        toggleDirectory('nested');
    });

    function toggleDirectory(dirname) {
        cy.get('.file-tree').contains('li', dirname).click();
    }

    function openFile(filename) {
        cy.get('.file-tree').contains('li', filename).click();
        cy.url().should('match', /\/files\/\d+/);
        cy.get('.file-viewer .loader').should('not.exist');
    }

    function addComment(selector, comment = 'comment') {
        cy.get(selector).first().click({ force: true });
        cy.get('.feedback-area.edit').first().within(() => {
            cy.get('textarea').type(comment);
            cy.get('.submit-feedback .submit-button').submit('success', {
                waitForDefault: false,
            });
        });
        cy.get('.feedback-area:not(.edit)').should('exist');
    }

    context('Inline feedback preference', () => {
        function openSettings() {
            cy.get('.local-header .settings-toggle').click();
            return cy.get('.settings-content').should('be.visible');
        }

        function closeSettings() {
            cy.get('.local-header .settings-toggle').click();
            return cy.get('.settings-content').should('not.be.visible');
        }

        function getOptionTR(name) {
            return openSettings().contains('tr', name);
        }

        function hideComments() {
            getOptionTR('Inline feedback')
                .find('.toggle-container .label-off').click();
            closeSettings();
        }

        function showComments() {
            getOptionTR('Inline feedback')
                .find('.toggle-container .label-on').click();
            closeSettings();
        }

        it('should hide feedback when disabled', () => {
            function hideCommentsCheck() {
                hideComments();
                cy.get('.feedback-area').should('not.exist');
                showComments();
                cy.get('.feedback-area').should('exist');
            }

            openFile('timer.c')
            addComment('.inner-code-viewer .line');
            hideCommentsCheck();

            openFile('Graaf vinden');
            addComment('.inner-code-viewer .line');
            addComment('.result-cell .feedback-button');
            addComment('.markdown-wrapper .feedback-button');
            hideCommentsCheck();

            openFile('venn1.png');
            addComment('.image-viewer .feedback-button');
            hideCommentsCheck();

            openFile('thomas-schaper');
            addComment('.pdf-viewer .feedback-button');
            hideCommentsCheck();

            openFile('README.md');
            addComment('.markdown-viewer .feedback-button');
            hideCommentsCheck();
        });

        it('should be reset when going to another file', () => {
            openFile('timer.c');
            hideComments();
            openFile('lemon.c');
            getOptionTR('Inline feedback').find('.toggle-container')
                .should('have.attr', 'checked')
                .should('eq', 'checked');
        });

        it('should make it impossible to add comments', () => {
            openFile('timer.c');
            hideComments();
            cy.get('.inner-code-viewer').should('not.have.class', 'editable');
            cy.get('.inner-code-viewer .line').first().click();
            cy.get('.feedback-area').should('not.exist');

            openFile('Graaf vinden');
            hideComments();
            cy.get('.inner-code-viewer').should('not.have.class', 'editable');
            cy.get('.inner-code-viewer .line').first().click();
            cy.get('.feedback-area').should('not.exist');
            cy.get('.inner-result-cell + .feedback-button').should('not.exist');
            cy.get('.inner-markdown-viewer + .feedback-button').should('not.exist');

            openFile('venn1.png');
            hideComments();
            cy.get('.image-viewer .feedback-button').should('not.exist');

            openFile('thomas-schaper');
            hideComments();
            cy.get('.pdf-viewer .feedback-button').should('not.exist');

            openFile('README.md');
            hideComments();
            cy.get('.markdown-viewer .feedback-button').should('not.exist');
        });
    });
});
