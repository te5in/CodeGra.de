Environment setup
==================

To make CodeGrade AutoTest as flexible as possible, it is possible to customize
the complete environment the tests are run in. Each separate assignment that
makes use of AutoTest runs on its own Virtual Private Server, to which you have
superuser rights and network access during the setup phase. Every VPS is shipped
with the latest LTS version of Ubuntu, which is **Ubuntu
18.04.2 LTS**.

After the Setup Phase is finished, a snapshot is created which is used to
initialize the containers used to run the actual tests on the student
submissions. The Setup Phase consists of the default installed software,
fixtures (which are available in the ``../fixtures/`` folder) and setup script.

There are multiple options for setting up your environment, which makes AutoTest
easy to use for simple cases yet very flexible for all advanced cases.

Default Installed Software
---------------------------

Each AutoTest VPS environment comes with pre-installed software that is
commonly used for testing and running student submissions. This body of software
is sufficient for most cases, which allows you to skip manually further setting
up the environment.

The following software is automatically installed in all environments:

- Python 2.7 *(with pip)*
- Python 3.6 *(with pip3)*
- Python 3.7 *(with pip3)*
- Java 8 *(openjdk-8-jdk)*
- Java 11 *(openjdk-11-jdk)*
- R *(r-base)*
- C *(clang)*
- Go *(golang)*
- Git
- Maven
- Flake8
- Numpy *(for Python2, Python3.6 and Python3.7)*
- SciPy *(for Python2, Python3.6 and Python3.7)*

Read the following sections to find out about extending this environment with
other required software.

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
    makes it possible to use *unextracted* archives as fixtures too.

Setup script
--------------

A setup script can be specified which runs prior to the tests to customize the
initial environment. Any script can be uploaded as fixture and subsequently
run with the command given in the *Setup script to run* input field.

This can be, for example, a bash script that installs software using apt and
extracts archives, or compiles unit tests.

.. note::
    **Network access** and **Superuser rights** are available during the Setup
    Phase.
