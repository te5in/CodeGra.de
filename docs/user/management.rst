.. _management-chapter:

Course and Assignment Management
========================================
The :fa:`cog` button next to courses or assignments is visible to all users with the right
permissions to manage courses or assignments. Clicking this button shows the corresponding
management page.

Additionally, clicking on the name of a course results in an overview of its assignments and
still allows to click the :fa:`cog` button on the bottom right to show the management page.

.. _course-management:

Course Management
-------------------
The course management page displays a list of all users (students, teachers and other roles) that are
*enrolled* in the course. The role of users can be changed here and new users can be added to the course.

.. note:: Course management is done in your learning management system if the course is connected, however managing roles and permissions is still done in CodeGrade.

The second tab shows an overview of all roles and their specific
permissions. Existing roles can be altered and completely new roles can be added
via the dialog on the bottom of the page. More information about the specific
course permissions can be found in the :ref:`next chapter
<permissions-chapter>`.

Creating a new Course
~~~~~~~~~~~~~~~~~~~~~~
Specific :ref:`site permissions <site-permissions>` are required to create a
course, usually this can be done only be site administrators. If these
permissions are set, a course can be created by navigating to the courses menu
and clicking the :fa:`plus` icon. The name for the new course can then be given.

Assignment Management
----------------------
Clicking the :fa:`cog` button next to a specific assignment shows the assignment management page. Usually all teachers and
course designers can manage courses. Next to basic settings as the assignment name and deadline this page provides some more advanced features.

.. _manage-assignment-state:

Assignment State
~~~~~~~~~~~~~~~~~~~
Three assignment states are available and can be set on the top right:

* :fa:`eye-slash` **Hidden** state: the assignment is invisible to students.
* :fa:`clock-o` **Open** state: the assignment is visible to students and students can hand in submissions before the deadline.
* :fa:`check` **Done** state: the assignment is visible to students and grading is finished.

Dividing Submissions
~~~~~~~~~~~~~~~~~~~~~
To randomly and automatically assign graders to all submissions the Divide Submission feature on the
assignment management page can be used. A list of all graders is displayed and after selecting the wanted graders
weights can be given to affect the workload per grader. The resulting percentage is the percentage of submissions the
grader will be randomly assigned to. Newly submitted submissions are automatically assigned to graders after dividing is performed.
Dividing submissions is consistent, so new submissions will get assigned to the same teaching assistant.

Manually assigning submissions is possible via the submission list, by selecting the grader using the 'Assigned to' dropdown dialog.

.. note:: When teachers manually assign themselves, weights are not updated to reflect this.

Linters
~~~~~~~~~
CodeGrade provides several linters (e.g. Flake8 or Pylint). A linter analyses
submissions to flag programming errors, bugs, stylistic errors, or suspicious
constructs, depending on the linter's characteristics. After selecting the right
linter and optionally writing a config file (custom config files can be given,
however using an empty config file is recommended, please consult the specific
linter's documentation for details on writing config files), the linter can be
run using the 'Run' button.

The output of the linter will be displayed in the :ref:`Codeviewer
<codeviewer-chapter>` and indicated by red line numbers that display the linter
output by hovering over. Linters can often be useful to provide a quick overview
of stylistic errors or bad constructs.

.. note::

    However linter output can be very useful when manually grading, they cannot
    be used to automatically assign grades based on the linter output.

CGIgnore File
~~~~~~~~~~~~~
The CGIgnore file acts as a *filter* to all submissions. It is formatted exactly like the common ``.gitignore`` files.
All files noted in the CGIgnore are ought to be excluded from submissions (e.g. no ``.tex`` LaTeX source files but only the PDF file).
Students that try to hand in a submission with excluded files get a warning and are given the option to cancel the submission, continue the
submission but delete the excluded file or continue the submission and include the excluded file.

.. warning:: Ignored files **can** be submitted if a student chooses to do so, however a warning is always shown.

Files to be excluded are pattern matched with the entries in the CGIgnore file. Literal filenames can be given or an ``*`` (asterisk)
can be used as wildcard (e.g. ``*.tex`` will exclude all files with the ``.tex`` extension). A more strict wildcard is the ``?`` (question mark)
which can be used to match exactly one character (e.g. ``assignment?.py`` will exclude all Python files that start with assignment and are
followed by one character like ``assignment1.py``). All entries in the CGIgnore file should be on new lines.

Finished Grading and Notifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
CodeGrade provides essential communication tools between graders in the shape of e-mail notifications. These notifications
rely on graders indicating that they are done grading by setting their state to 'Done' after all grading is finished.

.. warning:: It is possible to set a grader to the 'Done' state that did not finish grading all assigned submissions, a warning is shown in this case.

E-mail Notifications
^^^^^^^^^^^^^^^^^^^^^^
CodeGrade provides two types of e-mail notifications to enable essential communication between graders:

* **Graders** notification: send an e-mail at a specified date and time to all graders that have not yet finished grading.
* **Finished** notification: send an e-mail to a specified e-mail address to notify when all graders are finished grading.

.. note:: Notifications rely on the manually set status by the graders.

Plagiarism Detection
~~~~~~~~~~~~~~~~~~~~~~
CodeGrade offers built in plagiarism detection functionalities, to efficiently
and clearly detect for plagiarism on programming assignments.  Please consult
the :ref:`Plagiarism Detection <plagiarism-chapter>` chapter for more
information.

Rubrics
~~~~~~~~~~
Rubrics are an indispensable tool in modern day education and allow for easy and consistent grading between different graders and submissions.
Sophisticated rubrics can be made in CodeGrade. A basic rubric consist of multiple categories that all have multiple levels and corresponding
points. All components in a CodeGrade rubric can have a name and description.

A new category can be created by clicking the :fa:`plus` button. A name and
description can be given, furthermore a number of levels can be given. New
levels are automatically added by typing in previous levels and levels can be
removed by pressing the :fa:`times` button.

Each level can be assigned a number of points (usually descending). The total number of points is automatically incremented by the given
points but can be manually overridden if requested.

.. note:: A rubric is only saved after pressing the 'Submit' button, it is recommended to occasionally save the rubric to prevent losing work.

Uploading Submissions
~~~~~~~~~~~~~~~~~~~~~~~
Submissions can be uploaded via the assignment management page too. Using the *Upload submission* tool submissions can be uploaded as
any requested user: hand in submissions for students or hand in as administrator by selecting a user via the search bar.

.. _upload-blackboard-zip:

Uploading Blackboard Archives
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It is possible to combine CodeGrade with the Blackboard learning management system: handing in is done via Blackboard and grading and
presenting feedback via the stand-alone CodeGrade application. After exporting the submissions on Blackboard (see Blackboard documentation
`here <https://help.blackboard.com/Learn/Instructor/Assignments/Download_Assignments>`__), the downloaded archive can be uploaded using
Blackboard Zip tool in CodeGrade.

By uploading this archive, CodeGrade will add all students' corresponding CodeGrade accounts to the course and link their submissions correctly.
If a student does not yet have a CodeGrade account, a new account will be created.

.. warning:: BlackBoard uploading is an experimental feature that was tested working with BlackBoard 9, if an error occurs please contact us at help@codegra.de.


Creating a new Assignment
~~~~~~~~~~~~~~~~~~~~~~~~~
With the right :ref:`permissions <permissions-chapter>` new assignments for a
course can be created. To do this, select the course in the Course menu and
click on it to display its assignment list. A new assignment can now be created
for this course using the :fa:`plus` button on the bottom of the
menu-screen. Press *Add* after specifying a name for the assignment to create
it.
