Quickstart Guide
=================
CodeGrade is a blended learning application designed especially for modern
programming education. It is available as both a stand-alone web application and
as a module in your `LMS <lms.html>`__, with a combination of both possible.

After logging in to your CodeGrade account, an overview page displaying all
enrolled in courses their assignments is shown. You can always return to this
overview page by clicking the CodeGrade logo on top of the menu.

All further navigating on the side is done using this menu and its submenus. Use
the first menu item, the *User menu*, to `manage site preferences, account
information and snippets <preferences.html>`__. The second menu item, the
*Course menu*, gives an overview of all courses you are enrolled in or teach.
Clicking on a course will reveal a list of all its assignments. Additionally,
a list of your assignments, for all your courses, can be found in the
*Assignments menu*.

.. note:: With the right `permissions <permissions.html>`__, the :fa:`cog` button can be used to `manage <management.html>`__ a course or assignment.

Finally, this documentation can be found by pressing the little :fa:`question`
button on the bottom of the page. Next to this is the logout :fa:`power-off`
button.

Student Workflow
-----------------
You can hand in submissions for assignments in a CodeGrade course you are
enrolled in. Navigate and click to the assignment, either via the *Course menu*
to search by course or the *Assignments menu* to find an overview of all
assignments.

Click the *Browse* button to locate and hand in your submission to the
assignment. Press the *Submit* button to hand in the submission.

.. note:: CodeGrade supports handing in archives (e.g. ``.zip`` or ``.tar`` files) or individual files.

Once an assignment is graded and set to *Done* (indicated by :fa:`check`), you
can display your grade and feedback by clicking on your submission. The
Codeviewer allows you to display your line feedback, general feedback, filled in
rubric, linter output and grade. Please consult the
`Codeviewer for Students <codeviewer.html#codeviewer-for-students>`__ chapter
for more information.

Grading Workflow
-----------------
CodeGrade users with the right
`course permissions <permissions.html#course-permissions>`__ can grade
submissions. Navigate and click on the assignment, either via the *Course menu*
to search by course or the *Assignments menu* to find an overview of all
assignments, to find an overview of all submissions to this assignment. Click
on an individual assignment to start reviewing in the
`Codeviewer <codeviewer.html#codeviewer-for-teachers>`__.

.. note:: Submissions of an assignment can be automatically divided over all teachers. If the *Assigned to me* checkbox is on, only submission randomly assigned to you are displayed.

The Codeviewer allows you to navigate through all handed in files and folders
and display the code with highlighting in the browser. Additionally, ``PDF``
documents and images can be directly displayed in the browser too. Furthermore,
grading and reviewing can be done by adding line comments, filling in the
rubric, reviewing linter output or adding general feedback. Please consult the
`Codeviewer for Teachers <codeviewer.html#codeviewer-for-teachers>`__ chapter
for detailed information on all features.

.. note:: Use the top bar in the Codeviewer to quickly navigate between submissions that are assigned to you.

.. note:: Grading and reviewing is done most efficiently using the Filesystem.

Filesystem
-----------
CodeGrade offers a `Filesystem <https://fs-docs.codegra.de>`__ that can be used to locally
mount submissions and grade and run them in your local customary environment.

The filesystem can be installed using ``pip`` for Python **3.5** or higher with
the command: ``pip install CodeGra.fs``. The ``cgfs`` (*CodeGrade FileSystem*)
command can now be used to mount the filesystem with the following command:

``cgfs -p PASSWORD -u CODEGRADE_URL USERNAME mnt/``

In which ``PASSWORD`` should be replaced with your CodeGrade password,
``CODEGRADE_URL`` should be replaced with your CodeGrade instance's API (e.g.
``https://your-institute.codegra.de/api/v1``) and USERNAME should be replaced
by you CodeGrade username. Finally, ``mnt/`` should be an empty folder in your
current directory in which ``cgfs`` will mount.

After mounting is done, you can navigate to the ``mnt/`` folder in your
file manager or by opening a new terminal window to find all your courses,
assignments and submissions. Now the submissions can be locally run, reviewed
and (*automatically*) graded using the special files. Furthermore, teacher
revisions can be given.

Please consult the `Filesystem <https://fs-docs.codegra.de>`__ documentation for more
detailed information on installing and using the filesystem.

LMS Basic Workflow
-------------------------------
CodeGrade can be integrated into your learning management system through the
LTI standard (see the `LMS Integration <lms.html>`__ chapter for more
information on setting this up). Workflows for both students and teachers differ
slightly when using CodeGrade through an LMS, instead of the stand-alone
application.

Student LMS Workflow
~~~~~~~~~~~~~~~~~~~~~~
When entering a CodeGrade assignment in your learning management system, your
LMS account will automatically get linked to your current CodeGrade account or
a new CodeGrade account will get created if you do not have one yet (see
`Account Linking <lms.html#account-linking>`__ for details).

Handing in your submission and viewing your feedback and grade can all be done
in the CodeGrade window within your LMS. However, viewing feedback and grades
can also be done in CodeGrade's stand-alone environment. You will automatically
log in to this environment with a CodeGrade account linked to your LMS account
if you have previously opened a CodeGrade assignment through your LMS.

.. note:: It is possible to reset the password of this automatically generated LMS account, see `LMS Account Passwords <preferences.html#lms-account-passwords>`__ for more details.

Teacher LMS Workflow
~~~~~~~~~~~~~~~~~~~~~
After creating a CodeGrade assignment in your learning management system, the
corresponding course and assignment are automatically created on the CodeGrade
instance. Management of the course and assignment is mainly done via CodeGrade,
with some exceptions. Please consult `Creating LMS Courses or Assignments
<lms.html#creating-courses-or-assignments>`__ for more details.

Grading submissions in your CodeGrade assignment can be done in the CodeGrade
window in your LMS, but is recommended to be done on the CodeGrade stand-alone
website for more screen-space or via the filesystem. You will be automatically
logged into the CodeGrade account linked to your LMS account when going to
your CodeGrade instance in the same browser session as you used to visit or
create the CodeGrade assignment in your LMS, see
`Account Linking <lms.html#account-linking>`__ for details.

.. note:: It is possible to reset the password of this automatically generated LMS account (for instance to use the filesystem), see `LMS Account Passwords <preferences.html#lms-account-passwords>`__ for more details.

The grading process is now similar to that without LMS integration as described
earlier. Please keep in mind that grades are only passed back to your LMS after
manually setting the assignment state to *done* in CodeGrade. See
`LMS Grading <lms.html#grading>`__ for more details.
