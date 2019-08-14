Continuous Feedback
======================
CodeGrade Continuous Feedback allows students to instantly get insightful
automated feedback every time they hand in a new revision of their submission.
The tests that run in Continuous Feedback are (a subset of) the AutoTest tests,
this means that Continuous Feedback has the same security and reliability as
CodeGrade AutoTest.

Continuous Feedback results are preliminary, meaning they do not fill in the
rubric nor result in a final grade for the student. Rather, the results allow
students to revise their work and start processing feedback even before the
deadline.

Set-up
---------
Continuous Feedback uses the AutoTest configuration and tests. Enabling
Continuous Feedback for your assignment can be done by pressing the
**"Continuous Feedback"** button on the AutoTest page. When this button is
enabled, students will automatically and near instantly receive feedback for all
handed in submissions.

Differentiate between AutoTest and Continuous Feedback
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It is oftentimes wished to not include all tests in your Continuous Feedback
runs. Disable and hide an individual test for Continuous Feedback by toggling
the :fa:`eye` button next to this test. This results in the test not being
executed in the Continuous Feedback runs and hides details from students in the
AutoTest results.

.. note::
    It is good practice to disable heavy / long tests in the Continuous Feedback
    runs to optimize performance.
