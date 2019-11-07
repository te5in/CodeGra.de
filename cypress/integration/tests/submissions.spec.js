context('Submissions page', () => {
    let url;

    before(() => {
        cy.visit('/')
        cy.login('student1', 'Student1')
        cy.get('.assignment-state.assignment-state-Submitting').first()
            .parentsUntil('.assig-list-item').first()
            .click()
        cy.url().then($url => {
            url = $url;
        });
    });

    beforeEach(() => {
        cy.visit(url)
    })

    function getStudent(name, outer=false) {
        const inner = cy.get('.submissions-table .user').contains(name);
        if (outer) {
            return inner.parentsUntil('tbody').last()
        }
        return inner;
    }

    function giveGrade(name, grade) {
        getStudent(name).click()
        cy.get('.grade-viewer input[name=grade-input]').clear()
        if (grade != null) {
            cy.get('.grade-viewer input[name=grade-input]').type(`${grade}`)
        }
        cy.get('.grade-viewer .submit-grade-btn').submit('success');
        cy.visit(url)
    }

    it('should be on the submissions page', () => {
        cy.login('student1', 'Student1', false)

        cy.url().should('contain', 'submissions')
        cy.get('.submissions-table .user').contains('Student1').should('be.visible')
        getStudent('Student2').should('not.exist')
    })

    it('should be possible to hand something in', () => {
        cy.login('student1', 'Student1', false);

        cy.get('.multiple-files-uploader .dropzone').should('be.visible');
        const fileName = 'test_submissions/hello.py';

        cy.fixture(fileName, 'utf8').then(fileContent => {
            const lines = fileContent.split('\n');

            cy.get('.dropzone').upload(
                {
                    fileContent,
                    fileName,
                    mimeType: 'text/x-python',
                    encoding: 'utf8'
                },
                { subjectType: 'drag-n-drop' },
            );

            cy.get('.submission-uploader .submit-button').click();
            cy.url().should('contain', '/files/');

            cy.openCategory('Code');
            cy.get('.file-tree').contains('li', 'hello.py').click();

            cy.get('.inner-code-viewer .line').each(($line, i) => {
                cy.wrap($line).should('contain', lines[i]);
            });
        });
    });

    it('should not show a grade by default', () => {
        cy.login('robin', 'Robin', false)

        cy.get('input[name=submissions-filter]').type('Student1')
        getStudent('Student1', true).find('.submission-grade').contains('-')
        giveGrade('Student1', 5.0101)

        getStudent('Student1', true).find('.submission-grade').contains('5.01')
    })

    it('should be assigned to nobody by default', () => {
        cy.login('robin', 'Robin')

        getStudent('Student1', true).find('.assigned-to-grader select')
            .should('have.value', '')
            .should('contain', '-')
        cy.get('.cat-container .assigned-to-me-option').should('not.exist')

        getStudent('Student1', true).find('.assigned-to-grader select')
            .select('Robin')
            .should('contain', 'Robin')
        cy.get('.cat-container .assigned-to-me-option').should('be.visible')
        getStudent('Student2').should('exist')

        cy.get('.cat-container .assigned-to-me-option').click()
        getStudent('Student2').should('not.exist')

        getStudent('Student1', true).find('.assigned-to-grader select').select('-')
        cy.get('.cat-container .assigned-to-me-option').should('not.exist')
        getStudent('Student2').should('exist')
    })

    context('Filtering', () => {
        beforeEach(() => {
            cy.login('robin', 'Robin', false)
        });

        it('should be possible to filter', () => {
            getStudent('Student1').should('exist')
            getStudent('Student2').should('exist')

            cy.get('input[name=submissions-filter]').type('Student2')
            getStudent('Student1').should('not.exist')
            getStudent('Student2').should('exist')

            getStudent('Student2').click()
            cy.get('.submission-nav-bar').should('contain', 'Student2')
        })

        it('should be kept when going to a submission and back', () => {
            cy.get('input[name=submissions-filter]').type('Student2')
            cy.url().should('match', /[?&]q=Student2/)

            getStudent('Student2').click()
            cy.url()
                .should('match', /submissions\/\d+/)
                .and('match', /[?&]q=Student2/)
        });

        it('should be used in the navbar on the submission page', () => {
            cy.get('input[name=submissions-filter]').type('Student');
            cy.get('.submissions-table tbody tr td:first-child')
                .then($el => $el.get().map(el => el.textContent.trim()))
                .as('users');
            cy.get('.submissions-table tbody tr:first').click();

            cy.get('.submission-nav-bar .btn.prev').should('be.disabled');

            cy.get('@users').each((user, i, list) => {
                cy.get('.submission-nav-bar').should('contain', user);

                if (i < list.length - 1) {
                    cy.get('.submission-nav-bar .btn.next').click();
                } else {
                    cy.get('.submission-nav-bar .btn.next').should('be.disabled');
                }
            });
        });
    });

    context('Sorting', () => {
        function gradeOrder(order) {
            const els = cy.get('.submission-grade').each((item, index) => {
                cy.wrap(item).contains(order[index]);
            });
        }

        before(() => {
            cy.login('robin', 'Robin', false)
            cy.visit(url)

            giveGrade('Œlµo', null)
            giveGrade('Student4', 0)
            giveGrade('Student3', 1)
            giveGrade('Student2', 5)
            giveGrade('Student1', 10)
        });

        beforeEach(() => {
            cy.login('robin', 'Robin', false)
        });

        it('should sort correctly', () => {
            cy.get('.submissions-table thead').contains('Grade').click()
            gradeOrder(['-', '0.00', '1.00', '5.00', '10.00'])

            cy.get('.submissions-table thead').contains('Grade').click()
            gradeOrder(['10.00', '5.00', '1.00', '0.00', '-'])
        })

        it('should be kept when going to a submission and back', () => {
            cy.get('.submissions-table thead').contains('Grade').click()
            cy.url()
                .should('match', /[?&]sortBy=grade/)
                .should('match', /[?&]sortAsc=true/)

            getStudent('Student2').click()
            cy.url()
                .should('match', /[?&]sortBy=grade/)
                .should('match', /[?&]sortAsc=true/)

            cy.get('.local-header .back-button').click()
            cy.url()
                .should('match', /[?&]sortBy=grade/)
                .should('match', /[?&]sortAsc=true/)
            gradeOrder(['-', '0.00', '1.00', '5.00', '10.00'])
        });

        it('should be used in the navbar on the submission page', () => {
            cy.get('.submissions-table thead').contains('Grade').click()
            cy.get('.submissions-table tbody tr td:first-child')
                .then($el => $el.get().map(el => el.textContent.trim()))
                .as('users');
            cy.get('.submissions-table tbody tr:first').click();

            cy.get('.submission-nav-bar .btn.prev').should('be.disabled');

            cy.get('@users').each((user, i, list) => {
                cy.get('.submission-nav-bar').should('contain', user);

                if (i < list.length - 1) {
                    cy.get('.submission-nav-bar .btn.next').click();
                } else {
                    cy.get('.submission-nav-bar .btn.next').should('be.disabled');
                }
            });
        });
    });
})
