AutoTest
================================

AutoTest is CodeGrade's highly flexible and highly customizable Automatic
Grading Environment. With AutoTest you can fully configure a Virtual Machine
to suit the needs of your assignments. Via the intuitive user interface you can
easily create simple input/output tests or run custom programs or unit tests.

AutoTest provides a lightweight Virtual Machine for each submission within an
assignment running Ubuntu (Linux), this Virtual Machine is fully configurable
and you can install anything you want on this VM. Via the UI you can select
from many preconfigured base systems to easily install this on each VM. Each
assignment runs on a dedicated Virtual Private Server (VPS) providing a hard
division between assignments and maximum security and privacy. AutoTest is
secure by default and by design.

AutoTest Tests are grouped into Test Suites, these Test Suites are then connected
to a rubric category. This gives maximum feedback to students and forces teachers
to group their tests in a meaningful way.

Test Suites are grouped into Test Sets. Usually one Test Set is enough, but there
are some use-cases in which you would want to create multiple Test Sets.

Running AutoTest is easy and straightforward. After a run the results are visible
to students from within the Code Viewer.

.. toctree::
    :maxdepth: 1

    environment-setup
    test-sets
    test-suites
    tests
    running-autotest
    student-experience
    technical-details
    common-pitfalls
