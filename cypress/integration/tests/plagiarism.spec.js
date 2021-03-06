context('Plagiarsm', () => {
    let id = Math.floor(Math.random() * 100000);
    let user;
    let course;
    let assignment;

    function getOptionInput(option) {
        return cy.get('.plagiarism-runner .options-table tr')
            .contains('tr', option)
            .last()
            .find('input, select');
    }

    function selectLanguage(lang) {
        getOptionInput('Language').select(lang);
    }

    function setSuffixes(suf) {
        getOptionInput('Suffixes').type(suf);
    }

    function setSimilarity(sim) {
        getOptionInput('Minimal similarity').type(sim);
    }

    function setOldAssignments() {
        getOptionInput('Old assignments')
            .type(`${course.name} - Assignment B`)
            .parentsUntil('.multiselect')
            .parent()
            .find('.multiselect__element')
            .click();
    }

    function setOldSubmissions(archive, mimeType) {
        getOptionInput('Old submissions').uploadFixture(archive, mimeType);
    }

    function setBaseCode(archive, mimeType) {
        getOptionInput('Base code').uploadFixture(archive, mimeType);
    }

    function runPlagiarism(timeout = 60000) {
        cy.get('#plagiarism-run-button').submit('success');

        return cy.get('.runs-table tr.run-done:last-child', {
            timeout,
        }).should('exist');
    }

    before(() => {
        cy.visit('/');

        cy.createCourse(`Plagiarism ${id}`, [
            { name: 'robin', role: 'Teacher' },
        ]).then(res => {
            course = res;

            // Assignment A is the assignment we will run all tests on.
            cy.createAssignment(course.id, `Assignment A`, {
                bbZip: true,
            }).then(res => {
                assignment = res;

                // Assignment B is the "old assignment"
                cy.createAssignment(course.id, `Assignment B`, {
                    bbZip: true,
                });
            });
        });
    });

    beforeEach(() => {
        cy.login('robin', 'Robin')
        cy.visit(`/courses/${course.id}/assignments/${assignment.id}`);

        cy.get('.page.manage-assignment .local-header')
            .should('contain', assignment.name);
        cy.openCategory('Plagiarism');
    });

    it('should run without options', () => {
        selectLanguage('Python 3');
        setSimilarity(0);
        runPlagiarism().click();

        cy.get('.overview-table tbody tr:not(.table-warning)')
            .should('not.have.class', 'b-table-empty-row');
    });

    it('should run with the sufffixes option', () => {
        selectLanguage('Python 3');
        setSimilarity(0);
        setSuffixes('.py');
        runPlagiarism().click();

        cy.get('.overview-table tbody tr:not(.table-warning)')
            .should('not.have.class', 'b-table-empty-row');
    });

    it('should run with the old assignments option', () => {
        selectLanguage('Python 3');
        setSimilarity(99);
        setOldAssignments('Assignment 2');
        runPlagiarism().click();

        // There should be matches of 100% because both assignments
        // have the exact same code.
        cy.get('.overview-table tbody tr:not(.table-warning)')
            .should('not.have.class', 'b-table-empty-row')
            .and('be.visible')
            .contains('tr', '*')
            .contains('tr', '100.00')
            .first()
            .click();
        cy.get('.plagiarism-detail')
            .should('be.visible')
            .find('.card-header :not(a).text-muted')
            .should('be.visible');
    });

    it('should run with the old submissions option', () => {
        selectLanguage('Python 3');
        setSimilarity(99);
        setOldSubmissions('test_blackboard/bb.zip', 'application/zip');
        runPlagiarism().click();

        // There should be matches of 100% because both assignments
        // have the exact same code.
        cy.get('.overview-table tbody tr:not(.table-warning)')
            .should('not.have.class', 'b-table-empty-row')
            .and('be.visible')
            .contains('tr', '*')
            .contains('100.00')
            .first()
            .click();
        cy.get('.plagiarism-detail')
            .should('be.visible')
            .find('.card-header :not(a).text-muted')
            .should('be.visible');
    });

    it('should run with the base code option', () => {
        selectLanguage('Python 3');
        setSimilarity(0);
        setBaseCode('test_blackboard/bb-devin.zip', 'application/zip');
        runPlagiarism().click();

        cy.get('.overview-table tbody tr:not(.table-warning)')
            .should('not.have.class', 'b-table-empty-row')
            .and('be.visible')
            .and('not.contain', 'Devin Hillenius');
    });

    it('should delete runs when the delete button is clicked', () => {
        // Make sure there's at least one result to delete. Uses an unusual
        // value for similarity to make sure the run will not be denied because
        // of a run with the same settings.

        selectLanguage('Python 3');
        setSimilarity(11);
        runPlagiarism();

        cy.get('.runs-table .run-done:last .run-delete .submit-button').submit('success', {
            hasConfirm: true,
            waitForDefault: false,
        });
    });

    it('should have back buttons on the overview and detail pages', () => {
        selectLanguage('Python 3');
        setSimilarity(12);
        runPlagiarism().click();

        cy.get('.overview-table tbody tr:not(.table-warning):first').click();

        cy.get('.local-header .back-button').click();
        cy.get('.overview-table');
        cy.get('.local-header .back-button').click();
        cy.get('.plagiarism-runner');
    });

    // This test is skipped for now because Cypress detection for the download
    // dialog is not yet available (but it will be soon!)
    it.skip('should show the run log when the button on the overview page is clicked', () => {
        selectLanguage('Python 3');
        setSimilarity(10);
        runPlagiarism().click();

        cy.get('.local-header .download-btn').click();
    });
})
