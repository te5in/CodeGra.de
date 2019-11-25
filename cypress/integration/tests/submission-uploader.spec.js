context('Submission uploader', () => {
    let course;
    let assignment;

    function goToManage() {
        cy.visit(`/courses/${course.id}/assignments/${assignment.id}`);
        return cy.get('.page.manage-assignment').should('be.visible');
    }

    function goToSubmissions() {
        cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions`);
        return cy.get('.page.submission-list').should('be.visible');
    }

    function toggleTestSubmission() {
        cy.get('.submission-uploader')
            .contains('.custom-checkbox', 'Test submission')
            .find('input')
            .click({ force: true });
    }

    function setUploadAuthor(author) {
        cy.get('.submission-uploader')
            .find('.multiselect')
            .multiselect([author]);
    }

    function getGitCheck() {
        return cy.get('.manage-assignment')
            .contains('.custom-checkbox', 'GitHub/GitLab')
            .find('input[type="checkbox"]');
    }

    function toggleGitSubs(value = true) {
        return getGitCheck()
            .should(value ? 'not.be.checked' : 'be.checked')
            .click({ force: true }) // Actual <input> is invisible.
            .parentsUntil('fieldset')
            .find('.submit-button')
            .submit('success');
    }

    function getFileCheck() {
        return cy.get('.manage-assignment')
            .contains('.custom-checkbox', 'File uploader')
            .find('input[type="checkbox"]');
    }

    function toggleFileSubs(value = true) {
        return getFileCheck()
            .should(value ? 'not.be.checked' : 'be.checked')
            .click({ force: true })
            .parentsUntil('fieldset')
            .find('.submit-button')
            .submit('success');
    }

    before(() => {
        cy.visit('/');
        cy.createCourse('SubmissionUploader', [
            { name: 'student1', role: 'Student' },
            { name: 'robin', role: 'Teacher' },
        ]).then(res => {
            course = res;
        });
    });

    beforeEach(() => {
        cy.login('admin', 'admin');
    });

    context('No deadline set', () => {
        before(() => {
            cy.createAssignment(course.id, 'NoDeadline', {
                state: 'open',
            }).then(res => {
                assignment = res;
            });
        });

        beforeEach(() => {
            goToSubmissions();
        });

        it('should not be visible to teachers when the assignment has no deadline', () => {
            cy.login('robin', 'Robin');
            cy.get('.page.submission-list')
                .should('be.visible');

            cy.get('.submission-uploader')
                .should('not.exist');
            cy.get('.submission-list .alert-warning')
                .should('be.visible')
                .text()
                .should('contain', 'The deadline for this assignment has not yet been set. You can update the deadline here.');
            cy.get('.submission-list .alert-warning')
                .contains('a', 'here')
                .should('be.visible');
        });

        it('should not be visible to students when the assignment has no deadline', () => {
            cy.login('student1', 'Student1');
            cy.get('.page.submission-list')
                .should('be.visible');

            cy.get('.submission-uploader')
                .should('not.exist');
            cy.get('.page.submission-list .submission-list')
                .should('be.visible');
            cy.get('.submission-list .alert-warning')
                .should('be.visible')
                .text()
                .should('contain', 'The deadline for this assignment has not yet been set. Please ask your teacher to set a deadline before you can submit your work.');
        });
    });

    context.skip('Test student checkbox', () => {
        before(() => {
            cy.createAssignment(course.id, 'TestStudentCheckbox', {
                state: 'open',
            });
        });

        beforeEach(() => {
            goToSubmissions();
        });

        it('should not be visible for students', () => {
        });

        it('should be visible for teachers', () => {
        });

        it('should be disabled if a submission author is set', () => {
        });
    });

    context.skip('Other author', () => {
        before(() => {
            cy.createAssignment(course.id, 'OtherAuthorCheckbox', {
                state: 'open',
            });
        });

        beforeEach(() => {
            goToSubmissions();
        });

        it('should not be visible for students', () => {
        });

        it('should be visible for teachers', () => {
        });

        it('should be disabled if the Test Student checkbox is selected', () => {
        });
    });

    context.only('File submissions', () => {
        before(() => {
            cy.createAssignment(course.id, 'FileSubmissions', {
                state: 'open',
                deadline: 'tomorrow',
            }).then(res => {
                assignment = res;
            });
        });

        it('should hide the file uploader when file submissions are disabled', () => {
            goToManage();
            // We must enable git submissions to be able to disable file
            // submissions.
            toggleGitSubs();
            toggleFileSubs(false);
            cy.get('.submission-uploader')
                .find('.multiple-files-uploader')
                .should('not.exist');
            toggleFileSubs();
            cy.get('.submission-uploader')
                .find('.multiple-files-uploader')
                .should('exist');
        });
    });

    context('Git submissions', () => {
        let i = 0;

        beforeEach(() => {
            cy.createAssignment(course.id, `GitSubmissions${i++}`, {
                state: 'open',
                deadline: 'tomorrow',
            }).then(res => {
                assignment = res;
            });
        });

        function getGitLink(shouldFind = true) {
            return cy.get('.submission-uploader').find('.git-link').should(
                shouldFind ? 'exist' : 'not.exist',
            );
        }

        function openWebhookModal() {
            getGitLink().click();
            return cy.get('#git-instructions-modal').should('exist');
        }

        function closeWebhookModal() {
            cy.get('@modal')
                .find('button.close')
                .click();
            cy.get('@modal')
                .should('not.be.visible');
        }

        function getWebhookData(provider = 'github') {
            cy.wrap({}).as('webhookData');

            openWebhookModal().as('modal');

            cy.get('@modal')
                .find(`.logo.${provider}`)
                .click();
            cy.get('@modal')
                .find('.public-key')
                .text()
                .then(publicKey =>
                    cy.get('@webhookData').then(data => { data.publicKey = publicKey }),
                );
            cy.get('@modal')
                .find('.next-button').click();
            cy.get('@modal')
                .find('.webhook-url .form-control')
                .text()
                .then(url =>
                    cy.get('@webhookData').then(data => { data.url = url }),
                );
            cy.get('@modal')
                .find('.webhook-secret .form-control')
                .text()
                .then(secret =>
                    cy.get('@webhookData').then(data => { data.secret = secret }),
                );

            closeWebhookModal();

            return cy.get('@webhookData');
        }

        it('should not show git instructions when git submissions are disabled', () => {
            goToManage();
            getGitCheck().should('not.be.checked');
            getGitLink(false);
            goToSubmissions();
            getGitLink(false);
        });

        it('should show git instructions when git submissions are enabled', () => {
            goToManage();
            toggleGitSubs();
            getGitLink();
            goToSubmissions();
            getGitLink();

            cy.login('student1', 'Student1');
            goToSubmissions();
            getGitLink();
        });

        it('should show a modal upon clicking the git instructions link', () => {
            goToManage();
            toggleGitSubs();

            function checkPages(provider) {
                openWebhookModal().as('modal');

                cy.get('@modal')
                    .find(`.logo.${provider}`)
                    .should('exist')
                    .click();
                cy.get('@modal')
                    .find('.next-button')
                    .click()
                    .should('be.visible')
                    .click()
                    .should('not.be.visible');
                cy.get('@modal')
                    .find('.prev-button')
                    .click()
                    .should('be.visible')
                    .click()
                    .should('be.visible')
                    .click()
                    .should('not.be.visible');

                closeWebhookModal();
            }

            checkPages('github');
            checkPages('gitlab');
        });

        it('should show the same values for GitHub and GitLab', () => {
            goToManage();
            toggleGitSubs();

            getWebhookData('github').then(githubData => {
                getWebhookData('gitlab').should('deep.eq', githubData);
            });
        });

        it('should show different values for the current user, other user, test user', () => {
            goToManage();
            toggleGitSubs();

            getWebhookData().as('currentUserData');

            toggleTestSubmission();
            getWebhookData().as('testStudentData');
            toggleTestSubmission();

            setUploadAuthor('student1');
            getWebhookData().as('realStudentData');

            cy.getAll(['@currentUserData', '@testStudentData', '@realStudentData']).then(
                ([currUser, testUser, realUser]) => {
                    expect(currUser).not.to.deep.equal(testUser);
                    expect(testUser).not.to.deep.equal(realUser);
                    expect(realUser).not.to.deep.equal(currUser);
                });
        });

        it('should change the instruction link text when test submission is checked', () => {
            goToManage();
            toggleGitSubs();

            getGitLink().text().then(gitLinkText => {
                toggleTestSubmission();
                getGitLink().text()
                    .should('not.eq', gitLinkText)
                    .should('contain', 'test student');
            });
        });

        it('should change the instruction link text when an author has been specified', () => {
            goToManage();
            toggleGitSubs();

            getGitLink().text().then(gitLinkText => {
                setUploadAuthor('student1');
                getGitLink().text()
                    .should('not.eq', gitLinkText)
                    .should('contain', 'Student1');
            });
        });
    });
});
