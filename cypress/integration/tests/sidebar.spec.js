context('Sidebar', () => {
    before(() => {
        cy.visit('/');
    });

    it('should be possible to create a course', () => {
        const course = `Course ${Math.floor(Math.random() * 10000)}`;

        cy.login('admin', 'admin');

        // Make sure we have the "Create course" permission.
        cy.setSitePermission('Create course', 'Admin', true);
        cy.visit('/');

        cy.get('.sidebar .sidebar-entry-courses').click();
        cy.get('.sidebar .add-course-button').click();
        cy.get('.popover .submit-input input').type(course);
        cy.get('.popover .submit-input .btn').click();

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

        cy.get('.sidebar .add-assignment-button').click();
        cy.get('.popover .submit-input input').type(assig);
        cy.get('.popover .submit-input .btn').click();

        // Wait for manage-assignment page to be loaded.
        cy.get('.page.manage-assignment').should('exist');
        cy.get('.local-header').should('contain', assig);
    });
});
