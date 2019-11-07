context('Submission uploader', () => {
    let course;

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
        let assignment;

        before(() => {
            cy.createAssignment(course.id, 'NoDeadline', {
                state: 'open',
            }).then(res => {
                assignment = res;
            });
        });

        beforeEach(() => {
            cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions`);
            cy.get('.page.submission-list').should('be.visible');
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
            cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions`);
            cy.get('.page.submission-list').should('be.visible');
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
            cy.visit(`/courses/${course.id}/assignments/${assignment.id}/submissions`);
            cy.get('.page.submission-list').should('be.visible');
        });

        it('should not be visible for students', () => {
        });

        it('should be visible for teachers', () => {
        });

        it('should be disabled if the Test Student checkbox is selected', () => {
        });
    });
});
