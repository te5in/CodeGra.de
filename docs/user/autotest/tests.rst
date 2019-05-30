Tests
========

Within a Category you can create the actual tests. There are several different
tests, which offers a lot of flexibility.

IO Test
---------

The IO Test is the most common test to create. This is a test in which you
specify an input to a program and an expected output. If the students' program
returns the same output as expected, the test passes and they achieve points.

Setup
~~~~~~~

Setting up an IO test is straightforward.

- Give your IO test a meaningful name. Make sure this name is relevant, as this is the first feedback a student will receive.
- Specify which program to execute (this command is executed from within the student directory).

Then, you can specify all input and output combinations you want to check for this program.

- Give it a meaningful name.
- Give the input to the program, either as command-line arguments or input via standard in.
- Select options.

  - Case insensitive: ignore case in comparing the expected output and actual output.
  - Ignore trailing whitespace: trim all trailing whitespacing from the start and end.
  - Substring: the expected output should be a substring of the actual output.
  - Regex: the expected output is a Python3 regex which should match with the actual output.

Use the :fa:`plus` button in the bottom left corner to create a new input/output
combination.

Use-cases
~~~~~~~~~~

Run Program Test
-----------------

Use-cases
~~~~~~~~~~~~

Capture Points Test
---------------------

Use-cases
~~~~~~~~~~~

Checkpoints
---------------

Use-cases
~~~~~~~~~~
