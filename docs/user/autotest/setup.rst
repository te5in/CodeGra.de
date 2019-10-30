.. _autotest-setup:

Setup
==================

To make CodeGrade AutoTest as flexible as possible, it is possible to customize
the complete environment the tests are run in. Each separate assignment that
makes use of AutoTest runs on its own Virtual Server in the cloud, to which you
have superuser rights and network access during the setup phase. Every server on
official CodeGrade instances runs with the latest LTS version of Ubuntu, which
is **Ubuntu 18.04.2 LTS**.

After the Setup Phase is finished, a snapshot is created which is used to
initialize the containers used to run the actual tests on the student
submissions. The Setup Phase consists of the default installed software,
fixtures (the location of the fixtures directory is random for every category
and setup script to make it more virtually impossible for students to guess the
location and changes. The location is stored in the ``$FIXTURES`` environment
variable) and setup script.

.. warning::
    Setup scripts and other scrips (fixtures) that are executed have to use
    **Unix Line Endings (LF)** and **not** Windows Line Endings (CRLF)!

There are multiple options for setting up your environment, which makes AutoTest
easy to use for simple cases yet very flexible for all advanced cases.

Default Installed Software
---------------------------

Each AutoTest VPS environment comes with pre-installed software that is
commonly used for testing and running student submissions. This body of software
is sufficient for most cases, which allows you to skip manually further setting
up the environment.

The following software is automatically installed in all environments, all
versions, except for Python, are lower bounds, as all packages are always
updated to the latest version shipped by Ubuntu:

- Python 2.7 *(with pip)*
- Python 3.6 *(with pip3)*
- Python 3.7 *(with pip3)*
- Java 8 *(openjdk-8-jdk)*
- Java 11 *(openjdk-11-jdk)*
- Jupyter/IPython
- Mono *(6.4)*
- Node *(JavaScript 8.10)*
- Octave *(4.2.2)*
- R *(r-base 3.4)*
- C/C++ *(gcc 7 and clang 6 as compilers)*
- Go *(golang 1.10)*
- Git
- Maven
- Flake8
- Numpy *(for Python2, Python3.6 and Python3.7)*
- SciPy *(for Python2, Python3.6 and Python3.7)*
- Check *(unit test framework for C)*

Read the following sections to find out about extending this environment with
other required software.

.. _at-result-visibility:

Result visibility
----------------------

When a student uploads, AutoTest immediately runs on the handed in submission.
You can choose whether you want the student to directly be able to view the
AutoTest result (known as :ref:`Continuous Feedback <cont-feedback>`)
or that the student can only view the result when the assignment is set to "Done" (just like with any other
feedback).

The AutoTest rubric categories will be filled in automatically and directly in
either case if you have not created any hidden steps.

.. warning::
    If you have created hidden steps, AutoTest will be run again automatically
    within 30 minutes after the deadline, where the hidden steps are also executed.
    Before the deadline, hidden steps are never executed.

Rubric calculation
-------------------

There are two modes to fill in the rubric:

Minimum
~~~~~~~~~

A category's item will be chosen when the lower
bound of this item is reached (e.g. when a category has 4 items and 75% of the
tests succeed, the maximum item is filled in).

Maximum
~~~~~~~~

A category's item will be chosen when the upper bound of
this item is reached (e.g. you need 100% passed tests to have the maximum item filled in).

.. note::
    The percentages of the items in a category are independent of the amount of points
    given to them. E.g. if you have 4 items, item 1 is always 0%-25%, item 2 is 25%-50% and so forth.

Uploading fixtures
--------------------

Fixtures can be optionally uploaded to the AutoTest VPS. Fixtures are files you
can upload prior to the test, which will be available in every separate test
container. Use cases are files used as setup script (see next section), unit
tests, custom software to run or install and test input.

Select the fixtures to be uploaded and submit these to upload. A list of
previously uploaded fixtures can be found above the upload dialog and managed
here too.

.. warning::
    Archives are **not** automatically extracted when uploading fixtures. This
    makes it possible to use *unextracted* archives as fixtures too. Use the
    commands ``tar xfvz $FIXTURES/ARCHIVE.tar.gz`` or
    ``unzip $FIXTURES/ARCHIVE.zip`` to extract archives manually. Be careful
    with the permissions, we recommend running ``chown -R codegrade:codegrade
    $FIXTURES/dir`` and ``chmod -R 750 $FIXTURES/dir`` after extracting.

Global setup script
---------------------

A setup script can be specified which runs prior to the tests to customize the
initial environment. Any script can be uploaded as fixture and subsequently
run with the command given in the *Global setup script to run* input field.

This can be, for example, a bash script that installs software using apt and
extracts archives, or compiles unit tests.

If you need to setup or compile software for each student specifically and not
globally, use the *Per student setup script* for this. Install any packages
using the *Global setup script* as this will greatly increase the speed of
AutoTest Runs

.. warning::
    Setup scripts and other scrips (fixtures) that are executed have to use
    **Unix Line Endings (LF)** and **not** Windows Line Endings (CRLF)!

.. note::
    **Network access** and **Superuser rights** are available during the Setup
    Phase.

Per student setup script
---------------------------

Use the per student setup script to compile, for example, each submission's code.

.. note::
    If you want compiling to be part of a test, use the *Run program* test for
    this.
