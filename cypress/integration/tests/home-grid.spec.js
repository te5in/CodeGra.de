context('HomeGrid', () => {
    beforeEach(() => {
        cy.visit('/');
    });

    it('should show all courses with gear', () => {
        cy.login('robin', 'Robin');
        cy.visit('/');
        cy.get('.page.home .home-grid').should('exist');
        cy.get('.course-wrapper .course-name').should('contain', 'Programmeertalen');
        cy.get('.course-wrapper .course-manage').should('have.length.at.least', 2);
    });

    it('should not show a gear for students', () => {
        cy.login('student1', 'Student1');
        cy.visit('/');
        cy.get('.page.home .home-grid').should('exist');
        cy.get('.course-wrapper .course-name').should('contain', 'Programmeertalen');
        cy.get('.course-wrapper .course-manage').should('have.length', 0);
    });

    it('should go the submissions of an assignment when clicking', () => {
        cy.login('robin', 'Robin');
        cy.visit('/');
        cy.get('.page.home .home-grid').should('exist');
        cy.get('.course-wrapper .assig-list-item').first().click();
        cy.url().should('match', /.+assignments\/[0-9]+\/submissions.*/);
    });

    it('should go the manage course page when clicking gear', () => {
        cy.login('robin', 'Robin');
        cy.visit('/');
        cy.get('.page.home .home-grid').should('exist');
        cy.get('.course-wrapper .course-manage').first().click();
        cy.url().should('match', /\/courses\/[0-9]+/);
    });
});
