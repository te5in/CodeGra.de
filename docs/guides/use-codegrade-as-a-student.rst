How to use CodeGrade as a student
================================================

Using CodeGrade as a student is easy and offers you the ability to get a lot
more feedback and optionally automated test results.

When you open an assignment in CodeGrade or your LMS (Blackboard, Brightspace,
Canvas, Moddle, etc.) you are presented with a number of actions you can
perform.

- **Latest submission**: Go to your latest submission.

- **Upload files**: Create a new submission by uploading files.

- **Set up Git**: Show instructions on how to connect a Git provider to your
  assignment, this allows you to create submissions by pushing to a Git
  repository.

- **Rubric**: Show the rubric of this assignment.

- **Groups**: Create and/or join groups.

- **Course feedback**: Show an overview of the feedback you received to all
  assignments of this course.

.. note::
    Some of these are not available when they are not applicable, e.g. when an
    assignment is not set up as a group assignment, the groups button will be
    hidden.

Handing in
-----------

1. Click the "Upload files" button.

2. Optionally, if the teacher has set hand-in instructions, they are displayed
   at the top of the page. Make sure to follow your teacher's requirements when
   uploading files!

3. You can either drag and drop files onto the upload field or select them via
   your browser’s file picker dialog. You can either upload separate files, or
   an archive (such as a zip or tar). Archives are automatically extracted (but
   archives contained in other archives are not).

4. Press submit.

5. If the teacher enabled Continuous Feedback, you will now be able to see
   Automated Test results coming in (this might take a few minutes).

.. note::

    Keep in mind that Continuous Feedback is preliminary, and the rubric will
    not yet be filled in. You only get a grade after the deadline when the
    teacher graded your assignment.

6. Click on tests to see why they succeeded or failed. Improve your code and
   try again.

.. note::

    Always test your code first on your own system to make sure it works,
    before uploading to CodeGrade.

Handing in with Git
~~~~~~~~~~~~~~~~~~~~~

Some CodeGrade assignments allow you to hand in code by pushing to a Git
repository (GitLab or Github). If an assignment is set up to allow for Git
submissions the "Set up Git" button shows you instructions on how to set up a
deploy key and webhook URL for your repository.

.. note::

    Working in a group **and** handing in using Git? Make sure all members of
    the group have opened the CodeGrade assignment in Canvas, Moodle,
    Blackboard or Brightspace before handing in. *This does not apply to stand-
    alone usage of CodeGrade!*

.. warning::

    CodeGrade has a size limit for uploading submissions. Handing in via git
    can result in files exceeding this size limit to be silently deleted. Always
    check your submission in CodeGrade when working with large repositories.
    *If the size limit is exceeded, a file named ``cg-size-limit-exceeded``
    will show up in your submission.*

Viewing feedback
-----------------

After your assignment is graded, you can view your feedback through CodeGrade.

1. Navigate to the assignment, or click on your grade in the grade center.

2. View your feedback. On the Feedback overview, you can view your inline
   feedback comments with some context. Browse to the Code to view the inline
   feedback with all of your code. Finally, on the AutoTest tab you can view
   the output of the Automated Testing system.
