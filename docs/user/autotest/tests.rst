Tests
========

Within a Category you can create the actual tests. There are several different
tests, which offers enough flexibility to easily set up completely new tests or
execute any already existing testing tools.

Our philosophy is that even automatic assessment using AutoTest should be
feedback oriented: AutoTests should always give as much feedback to the student
as possible. This is already enforced by forcing linking Test and Rubric
Categories. Another way to maximise feedback to the students is by naming
your tests and inputs in a meaningful way, as this is the first feedback
students will receive from the tests.

.. note::

    Use weights per test (or per input of IO test) to differentiate between
    the importance of tests.

IO Test
---------

The IO Test is the most common test to create. This is a test in which you
specify an input to a program and an expected output. If the students' program
returns the same output as expected, the test passes and they achieve points.

A (student) program can be specified to be run in the IO tests, then, you can
specify all input and output combinations you want to check for this program.

Multiple options allow you to more flexibly compare the output of the program:

  - **Case insensitive**: ignore case in comparing the expected output and actual output.
  - **Ignore trailing whitespace**: trim all trailing whitespacing from the start and end.
  - **Substring**: the expected output should be a substring of the actual output.
  - **Regex**: the expected output is a *Python3 Regex* which should match with the actual output.

Use the :fa:`plus` button in the bottom left corner to create a new input/output
combination.

Use-cases
~~~~~~~~~~

Run Program Test
-----------------
The Run Program Test simply executes a specified program and checks the return
code or exit status of this program. Meaning, an exit status of 0 (or
**success**) returns in passing the test and any nonzero exit status (or
**failure**) returns in failing the test.

Use-cases
~~~~~~~~~~~~

Capture Points Test
---------------------
The Capture Points Test is an extension of the Run Program Test. It also
executes a specified program but instead of taking the exit status, captures
the output of this program. The output of the program can be captured using a
*Python Regex*. This output should be a valid *Python Float* number between **0
and 1**. This number is then multiplied with the weight of the Capture Points
Test to get to the final score of the test.


Use-cases
~~~~~~~~~~~

Checkpoints
---------------
Checkpoints can be used to add conditions to your Test Categories. A Check
Points block can be put in between tests, to only execute the proceeding tests
if enough points have been scored in the tests prior to the Check Points block.

Use-cases
~~~~~~~~~~
