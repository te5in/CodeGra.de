How to use CodeGrade as a student
================================================

Using CodeGrade as a student is easy and offers you the ability to get a lot
more feedback and optionally automated test results.

Handing in
-----------

1. Navigate to the assignment in Canvas, Moodle, Blackboard or Brightspace.

2. CodeGrade will now open and the first thing you see is the rubric.

3. Optionally: you can navigate to the hand-in instructions tab to view which files are required by your teacher.

4. Scroll down and click (or drag and drop) to upload your files. You can either upload files, or an archive (such as a zip or tar). Archives are automatically extracted by CodeGrade.

5. Press submit.

6. If the teacher enabled Continuous Feedback, you will now be able to see Automated Test results coming in (this might take a few minutes).

.. note::

    Keep in mind that Continuous Feedback is preliminary, and the rubric will not yet be filled in. You only get a grade after the deadline when the teacher graded your assignment.

7. Click on tests to see why they succeeded or failed. Improve your code and try again.

.. note::

    Always test your code first on your own system to make sure it works, before uploading to CodeGrade.

Handing in with Git
~~~~~~~~~~~~~~~~~~~~~
Some CodeGrade assignments allow you to hand in code via Git (GitLab or Github).
If this is possible, it should show up on the hand-in page. Follow the
instructions on this page to set up the deploy key and webhook for your
repository. If this is set up correctly, every ``git push`` you make will
automatically hand in on CodeGrade too.

.. note::

    Working in a group **and** handing in using Git? Make sure all members of
    the group have opened the CodeGrade assignment in Canvas, Moodle,
    Blackboard or Brightspace before handing in. *This does not apply to stand-
    alone usage of CodeGrade!*

.. warning::

    CodeGrade has a size limit for uploading submissions. Handing in via git
    can result in files exceeding this size limit to be silently deleted. Always
    check your submission in CodeGrade when working with large repositories.
    *If the size limit is exceeded, the ``cg-size-limit-exceeded`` will show up
    in your submission.*

Viewing feedback
-----------------

After your assignment is graded, you can view your feedback through CodeGrade.

1. Navigate to the assignment, or click on your grade in the grade center.

2. View your feedback. On the Feedback overview, you can view your inline feedback comments with some context. Browse to the Code to view the inline feedback with all of your code. Finally, on the AutoTest tab you can view the output of the Automated Testing system.
