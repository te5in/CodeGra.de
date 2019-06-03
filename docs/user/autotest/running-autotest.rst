Running AutoTest
==================
CodeGrade AutoTest is run on our dedicated servers. After setting up your
AutoTest tests, you can run it on all students at once. Press the **"Run"**
button on the top right corner to start the AutoTest run.

After preliminary processes are done and a runner picked up the job, the code
of students will subsequently be tested. An overview of all students eligible
for this AutoTest will be shown after the button is pressed, these are accompanied
by a score (ratio of number of points passed to the number of points possible)
and a state.

AutoTest States
-----------------
The multiple components of an AutoTest run can be in different states. Mouse
over over the icons in AutoTest to find more information on the specific state.

Entire AutoTest Run
~~~~~~~~~~~~~~~~~~~~
The following states can occur for the entire AutoTest run, normal behaviour is
subsequently waiting for runner, starting, running and done.

- :fa:`clock-o`: Waiting for runner.
- :fa:`exchange`: Changing runner.
- :fa:`clock-o`: Starting.
- :fa:`circle-o-notch`: Running.
- :fa:`check`: Done.
- :fa:`exclamation-triangle`: Test crashed, something unknown went wrong.
- :fa:`exclamation-triangle`: Test is timed out.

Student Runs
~~~~~~~~~~~~~
All individual student runs have a state that indicates whether a run is waiting,
running or finished with or without any problems.

- :fa:`clock-o`: Waiting to be started.
- :fa:`circle-o-notch`: Running.
- :fa:`check`: Test is finished without problems.
- :fa:`exclamation-triangle`: Test crashed, something unknown went wrong.
- :fa:`exclamation-triangle`: Test is timed out.

.. warning::

    Student run states **never** indicate the score of a student, they solely
    indicate whether a run finished with or without problems or whether it was
    timed out. Please consult the rubric and the states of the individual steps
    to find out about student scores.

Individual Steps
~~~~~~~~~~~~~~~~~
Finally, individual test steps have states. These states ultimately indicate
whether a single test is passed or failed.

- :fa:`clock-o`: Waiting to be started.
- :fa:`circle-o-notch`: Running.
- :fa:`check`: Test is finished and passed.
- :fa:`times`: Test is finished and failed.
- :fa:`exclamation-triangle`: Test is timed out.
