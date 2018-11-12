LMS Integration
=================

CodeGrade works together with learning management systems with the LTI
(*Learning Tools Interoperability*) standard. This chapter explains integrating
CodeGrade into your LMS and CodeGrade's behaviour when working together with
your LMS.

Canvas Integration
--------------------
CodeGrade works together with the popular open-source learning management system
`Canvas <https://www.canvaslms.com/>`__ through LTI. By integrating CodeGrade as
an external app in Canvas, CodeGrade assignments can be created.

CodeGrade can be added as an external app in Canvas using an XML file provided
by CodeGrade. Please consult the Canvas
`Documentation <https://community.canvaslms.com/docs/DOC-12601-421474560>`__
for instructions on adding external apps with XML.

It is now possible to create CodeGrade assignments in your Canvas course now.
Choose the *External Tool* option as *Submission Type* and select CodeGrade
in the *Find* menu.

.. note:: We recommend grading assignments in CodeGrade's stand-alone environment so more *screen-space* is be used for grading. Your are automatically logged in to this environment with a linked CodeGrade account after opening CodeGrade through Canvas.

BlackBoard Integration
------------------------
BlackBoard is supported in CodeGrade, however BlackBoard support is still an
experimental feature and only tested for BlackBoard 9.

CodeGrade allows the uploading of BlackBoard assignment archives. In this way,
the handing in and administration processes are done using BlackBoard, but
grading and reviewing feedback can be done in the CodeGrade stand-alone website.

More information on BlackBoard integration can be found
`here <management.html#uploading-blackboard-archives>`__.

Other LMS
-----------
CodeGrade is currently working on adding support for more learning management
systems too. Please `contact us <../about/contact.html>`__ for more information
about support of your learning management system.

CodeGrade LMS Behaviour
-------------------------
CodeGrade works together with the learning management system through LTI to
synchronise i.a. users, courses, assignments and grades. The following behaviour
is specified:

Creating Courses or Assignments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Course and assignment creation is done using your learning management
system environment. A corresponding CodeGrade course will automatically be
created When creating a CodeGrade assignment in your LMS. Management of your
assignment is mainly done in CodeGrade, however the assignment name, deadline
and state (e.g. *published* or *unpublished*) are managed in your LMS.

.. note:: Assignment and course names do not have to be unique.

.. note:: The LMS assignment states *published* and *unpublished* correspond respectively with CodeGrade's *open* and *hidden* states. CodeGrade's *done* state does not correspond with any LMS state and does not automatically change with LMS assignment management.

Users are not added to the CodeGrade course right away, however only added to
CodeGrade after opening the CodeGrade assignment in the LMS.
Users' roles are automatically saved from the LMS to CodeGrade when creating an
assignment, however these can be changed inside CodeGrade later on.

Grading
~~~~~~~~
When grading in CodeGrade is done, grades can be *passed back* to the LMS by
manually setting the assignment state to *done* in CodeGrade
(see `Assignment States <management.html#assignment-state>`__). Grades saved
when the assignment state already is *done* are automatically passed back to the
LMS.

.. warning:: Grades are **not** automatically passed back to the LMS but require the CodeGrade assignment state to be set to *done*.

Setting the CodeGrade assignment state back to *not done* will not automatically
hide grades in your LMS, but only hide the grades in CodeGrade. Setting the
assignment to muted in your LMS will also not hide the grades in CodeGrade if
the assignment state is *done*. This is because of the fact that
CodeGrade's *done* state does not correspond with any LMS state and does not
automatically change with LMS assignment management yet.

Account Linking
~~~~~~~~~~~~~~~~~
Accounts in your LMS are automatically linked or synchronised to CodeGrade
accounts. Opening a CodeGrade assignment in your LMS results in automatically
logging into CodeGrade with a CodeGrade account that is linked to your LMS
account. CodeGrade has specified behaviour for multiple cases:

* A new CodeGrade account will be created and linked to your LMS account if you open a CodeGrade assignment in your LMS and no existing CodeGrade account is linked yet.
* Your current CodeGrade account will be linked to your LMS account if you are logged in to CodeGrade and open a CodeGrade assignment in your LMS and your current CodeGrade account is not yet linked.
* You will automatically log in to the CodeGrade account linked to your LMS account if you open a CodeGrade assignment in your LMS and you are currently not logged into CodeGrade.
* You will switch CodeGrade accounts if you are currently logged in to a CodeGrade account but *another* CodeGrade account is linked to your LMS account while opening a CodeGrade assignment in your LMS.

.. note:: After opening a CodeGrade assignment in your LMS, you are automatically logged into CodeGrade with your linked account and can also open CodeGrade's stand-alone environment.
