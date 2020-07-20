context('Course Feedback', () => {
    context('No other assignments', () => {
        let seed = Math.round(100000 * Math.random());
        let course;
        let assignment;
        let submission;

        before(() => {
            cy.visit('/');
            cy.login('admin', 'admin');

            cy.createCourse(`Previous Feedback ${seed}`, [
                { name: 'student1', role: 'Student' },
            ]).then(res => {
                course = res;
                return cy.createAssignment(
                    course.id,
                    `Previous Feedback ${seed}-1`,
                    { deadline: 'tomorrow' },
                );
            }).then(res => {
                assignment = res;
                return cy.createSubmission(
                    assignment.id,
                    'test_submissions/hello.py',
                    { author: 'student1' },
                );
            }).then(res => {
                submission = res;
            });
        });

        it('should show a message that there is nothing to show', () => {
            cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions/${submission.id}`);
            cy.get('.submission-sidebar')
                .should('be.visible')
                .contains('.nav-item', 'Feedback')
                .click();
            cy.get('.course-feedback .loader')
                .should('not.exist');
            cy.get('.course-feedback .feedback-overview')
                .should('not.exist');
            cy.get('.course-feedback')
                .text()
                .should('contain', 'No other assignments in this course');
        });
    });

    context('With other assignments without submissions', () => {
        let seed = Math.round(100000 * Math.random());
        let course;
        let assignments = [];
        let submission;

        before(() => {
            cy.visit('/');
            cy.login('admin', 'admin');

            cy.createCourse(`Previous Feedback ${seed}`, [
                { name: 'student1', role: 'Student' },
            ]).then(res => {
                course = res;
                // Create some assignments.
                return cy.wrap(Array(2)).each((_, i) =>
                    cy.createAssignment(
                        course.id,
                        `Previous Feedback ${seed}-${i}`,
                        { deadline: 'tomorrow' },
                    ).then(a => assignments[i] = a),
                );
            }).then(() =>
                // Create a submission for each assignment.
                cy.createSubmission(
                    assignments[0].id,
                    'test_submissions/hello.py',
                    { author: 'student1' },
                ),
            ).then(res => {
                submission = res;
            });
        });

        it('should show a message that there is nothing to show', () => {
            cy.visit(`/courses/${course.id}/assignments/${assignments[0].id}/submissions/${submission.id}`);
            cy.get('.submission-sidebar')
                .should('be.visible')
                .contains('.nav-item', 'Feedback')
                .click();
            cy.get('.course-feedback .loader')
                .should('not.exist');
            cy.get('.course-feedback .feedback-overview')
                .should('not.exist');
            cy.get('.course-feedback .assignment-name')
                .should('have.length', 1)
                .should('contain', assignments[1].name)
                .should('contain', '(no submission)');
        });
    });

    function cartesian(xs, ys) {
        return xs.flatMap(x => ys.map(y => [x, y]), 1);
    }

    function addComments(sub) {
        const general = cy.patchSubmission(sub.id, {
            feedback: 'general feedback',
        });
        // Get the file tree.
        const inline = cy.authRequest({
            url: `/api/v1/submissions/${sub.id}/files/`,
            method: 'GET',
        }).then(res =>
            cy.wrap(cartesian(res.body.entries, [1, 2])).each(([file, lineNr]) =>
                // Create a comment thread.
                cy.authRequest({
                    url: '/api/v1/comments/',
                    method: 'PUT',
                    body: { file_id: Number(file.id), line: lineNr },
                }).then(thread =>
                    // Place a comment.
                    cy.authRequest({
                        url: `/api/v1/comments/${thread.body.id}/replies/`,
                        method: 'POST',
                        body: {
                            comment: `comment ${lineNr}`,
                            reply_type: 'markdown',
                        },
                    }).then(comment =>
                        // Place a reply
                        cy.authRequest({
                            url: `/api/v1/comments/${thread.body.id}/replies/`,
                            method: 'POST',
                            body: {
                                comment: `reply ${lineNr}`,
                                reply_type: 'markdown',
                                in_reply_to: comment.body.id,
                            },
                        }),
                    ),
                ),
            ),
        );
        return Cypress.Promise.all([general, inline]);
    }

    context('With other assignments with submissions', () => {
        let seed = Math.round(100000 * Math.random());
        let course;
        let assignments = [];
        let submissions = [];

        before(() => {
            cy.visit('/');
            cy.login('admin', 'admin');

            cy.createCourse(`Previous Feedback ${seed}`, [
                { name: 'student1', role: 'Student' },
            ]).then(res => {
                course = res;
                // Create some assignments.
                return cy.wrap(Array(4)).each((_, i) =>
                    cy.createAssignment(
                        course.id,
                        `Previous Feedback ${seed}-${i}`,
                        { state: 'open', deadline: 'tomorrow' },
                    ).then(a => assignments[i] = a),
                );
            }).then(() =>
                // Create a submission for each assignment.
                cy.wrap(assignments).each((assig, i) =>
                    cy.createSubmission(
                        assig.id,
                        'test_submissions/multiple_small_files.tgz',
                        { author: 'student1' },
                    ).then(sub => submissions[i] = sub),
                ).then(() =>
                    // Add comments to the 2nd and 4th submission, so that we
                    // have a submission in between them allowing us to test
                    // ordering.
                    Cypress.Promise.all([
                        addComments(submissions[1]),
                        addComments(submissions[3]),
                    ]),
                ),
            );
        });

        context('On the Submission page', () => {
            beforeEach(() => {
                cy.login(
                    'admin',
                    'admin',
                    `/courses/${course.id}/assignments/${assignments[0].id}/submissions/${submissions[0].id}`,
                );
                cy.openCategory('Code');
                cy.get('.submission-sidebar')
                    .should('be.visible')
                    .contains('.nav-item', 'Feedback')
                    .click();
                cy.get('.course-feedback .loader')
                    .should('not.exist');
            });

            it('should not be available to students', () => {
                cy.login(
                    'student1',
                    'Student1',
                    `/courses/${course.id}/assignments/${assignments[0].id}/submissions/${submissions[0].id}`,
                );
                cy.openCategory('Code');
                cy.get('.file-tree').should('be.visible');
                cy.get('.submission-sidebar').should('not.exist');
                cy.get('.course-feedback').should('not.exist');
            });

            it('should collapse submissions without feedback', () => {
                cy.get('.course-feedback')
                    .should('exist')
                    .contains('.badge', '0')
                    .parentsUpto('.x-collapse')
                    .should('have.class', 'x-collapsed');
            });

            it('should collapse all submissions by default', () => {
                cy.get('.course-feedback .badge')
                    .parentsUpto('.x-collapse')
                    .should('have.class', 'x-collapsed');
            });

            it('should not collapse submissions with feedback that match the filter', () => {
                cy.get('.course-feedback .filter')
                    .setText('comment{enter}');
                cy.get('.course-feedback .badge')
                    .parentsUpto('.x-collapse')
                    .should('have.class', 'x-collapsed');
            });

            it('should collapse submissions with feedback if none of the comments match the filter', () => {
                cy.get('.course-feedback .filter')
                    .setText('NO MATCH{enter}');
                cy.get('.course-feedback .badge')
                    .parentsUpto('.x-collapse')
                    .should('have.class', 'x-collapsed');
            });

            it('should sort submissions with matches before submissions without matches', () => {
                cy.get('.course-feedback .filter')
                    .setText('comment{enter}');
                cy.get('.course-feedback .badge')
                    .should('contain', '/')
                    .then($badges => {
                        const comments = $badges.get().map(b => b.innerText.trim().split(/\s*/)[0]);
                        const firstZero = comments.indexOf('0');
                        comments.slice(0, firstZero).forEach(c =>
                            expect(c).not.to.equal('0'),
                        );
                    });
            });

            it('should be possible to filter on general feedback', () => {
                // Without tag.
                cy.get('.course-feedback .filter')
                    .setText('general{enter}');
                cy.get('.course-feedback .card.general-feedback')
                    .should('contain', 'general feedback');
                // With tag.
                cy.get('.course-feedback .filter')
                    .setText('comment:general{enter}');
                cy.get('.course-feedback .card.general-feedback')
                    .should('contain', 'general feedback');
                // With tag but no match.
                cy.get('.course-feedback .filter')
                    .setText('comment:NOMATCH{enter}');
                cy.get('.course-feedback .card.general-feedback')
                    .should('not.exist');
            });

            it('should be possible to filter on inline feedback', () => {
                // Without tag.
                cy.get('.course-feedback .filter')
                    .setText('reply{enter}');
                cy.get('.course-feedback .feedback-reply')
                    .should('contain', 'reply');
                // With tag.
                cy.get('.course-feedback .filter')
                    .setText('comment:reply{enter}');
                cy.get('.course-feedback .feedback-reply')
                    .should('contain', 'reply');
                // With tag.
                cy.get('.course-feedback .filter')
                    .setText('comment:NOMATCH{enter}');
                cy.get('.course-feedback .feedback-reply')
                    .should('not.exist');
            });

            it('should be possible to filter on comment author', () => {
                // Without tag.
                cy.get('.course-feedback .filter')
                    .setText('admin{enter}');
                cy.get('.course-feedback .card.general-feedback')
                    .should('be.visible');
                cy.get('.course-feedback .reply-wrapper')
                    .should('be.visible');
                // With tag.
                cy.get('.course-feedback .filter')
                    .setText('author:admin{enter}');
                cy.get('.course-feedback .card.general-feedback')
                    .should('be.visible');
                cy.get('.course-feedback .reply-wrapper')
                    .should('be.visible');
                // With tag but no match.
                cy.get('.course-feedback .filter')
                    .setText('author:NOMATCH{enter}');
                cy.get('.course-feedback .card.general-feedback')
                    .should('not.exist');
                cy.get('.course-feedback .reply-wrapper')
                    .should('not.to.exist');
            });

            it('should fade comments that do not match a filter if another comment in the thread does match the filter', () => {
                cy.get('.course-feedback .filter')
                    .setText('comment{enter}');
                cy.get('.course-feedback')
                    .contains('.reply-wrapper', 'comment')
                    .within(() => {
                        cy.get('> .reply-gutter')
                            .should('not.have.class', 'faded');
                        cy.get('> .feedback-reply')
                            .should('not.have.class', 'faded');
                    });
                cy.get('.course-feedback')
                    .contains('.reply-wrapper', 'reply')
                    .within(() => {
                        cy.get('> .reply-gutter')
                            .should('have.class', 'faded');
                        cy.get('> .feedback-reply')
                            .should('have.class', 'faded');
                    });
            });

            it('should open file links in a new tab', () => {
                cy.get('.course-feedback .inner-inline-feedback-file .card-header a')
                    .should('have.attr', 'target', '_blank');
            });
        });

        context('On the Submissions page', () => {
            before(() => {
                cy.patchAssignment(assignments[1].id, { state: 'done' })
                    .then(res => assignments[1] = res);
                cy.patchAssignment(assignments[2].id, { state: 'hidden' })
                    .then(res => assignments[2] = res);

                cy.login(
                    'student1',
                    'Student1',
                    `/courses/${course.id}/assignments/${assignments[0].id}/submissions/`,
                );
                cy.get('.local-header')
                    .contains('.btn', 'Course feedback')
                    .click();
                cy.wait(2000);
                cy.get('[id^="submissions-page-course-feedback-modal"]')
                    .should('be.visible');
            });

            it('should be available to students', () => {
                cy.get('.course-feedback')
                    .should('be.visible');
            });

            it('should show feedback for all submissions in the course', () => {
                cy.get('.course-feedback .assignment-name')
                    .should('have.length', assignments.filter(a => a.state !== 'hidden').length);
            });

            it('should only show feedback when the student has the permission for that assignment', () => {
                cy.get('.course-feedback')
                    .contains('.badge', '5')
                    .should('have.length', assignments.filter(a => a.state === 'done').length);
            });
        });
    });
});
