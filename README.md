# Taskgrader
The taskgrader tool manages every step of grading a contest task, from the generation of test data to the grading of a solution output.

It allows for a wide variety of contest task types and languages to be evaluated, and is meant to be used both locally for tests and in contest evaluation settings.

It uses [isolate](https://github.com/ioi/isolate) as a sandbox to run solutions to limit execution time and memory, as well as their access to the environment.

**The full documentation is avaliable on [GitHub pages](http://france-ioi.github.io/taskgrader/) or in the `docs/` folder.**
