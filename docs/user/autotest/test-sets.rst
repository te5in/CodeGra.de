Test sets
===========

After settig up the AutoTest environment it's time to actually create some
tests. To do this, you first have to create a test set. This is done very
easily by pressing the **Add set** button.

A test set contains test suites. These test suites are connected to a rubric
category and contain the actual tests.

The test suites within a test set are executed independent of each other and
could be executed concurrently. This means that there is no order between
test suites within a test set (the tests within a test suite are executed in order).

For most use cases one test set is enough to do all your testing with.

Advanced use cases
--------------------

There is the possibility, however, to create multiple test sets. This can be
done, for example, if you only want to run certain test suites if other test
suites (in another test set) get a certain amount of points. After adding a
new test set you can set the amount of points in the footer of the set above.

Test sets are executed in order, and not concurrently.
