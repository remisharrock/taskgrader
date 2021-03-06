#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT

# This tool runs a series of tests against the taskgrader to check its behavior
# is as expected and the local configuration is good.


import argparse, json, os, subprocess, sys, threading, tempfile, traceback
import unittest

# Path to the taskgrader executable
CFG_TASKGRADER = os.path.normpath(os.path.dirname(os.path.abspath(__file__)) + '/../taskgrader.py')

def programExists(name):
    """Checks whether a program can be found in PATH."""
    def is_exe(path):
        return os.path.isfile(path) and os.access(path, os.X_OK)

    fpath, basename = os.path.split(name)
    if fpath and is_exe(name):
        return True
    else:
        for spath in os.environ['PATH'].split(os.pathsep):
            spath = spath.strip('"')
            if is_exe(os.path.join(spath, name)):
                return True
    return False


def communicateWithTimeout(subProc, timeout=0, input=None):
    """Communicates with subProc until its completion or timeout seconds,
    whichever comes first."""
    if timeout > 0:
        to = threading.Timer(timeout, subProc.kill)
        try:
            to.start()
            return subProc.communicate(input=input)
        finally:
            to.cancel()
    else:
        return subProc.communicate(input=input)


class FullTestBase(unittest.TestCase):
    """A full test is a test sending a full evaluation JSON to the taskgrader,
    and checking whether the outputJson returns expected results."""

    def assertVariableEqual(self, varName, assertedValue):
        """Tests whether the variable pointed by self.`varName` is equal to
        assertedValue."""
        try:
            var = eval("self." + varName)
        except:
            self.details['bad'].append('`%s` does not exist (should be equal to `%s`)' % (varName, assertedValue))
            return False

        if isinstance(var, basestring):
            var = var.strip()
            assertedValue = assertedValue.strip()

        if var == assertedValue:
            self.details['good'].append('`%s` == `%s`' % (varName, assertedValue))
            return True
        else:
            self.details['bad'].append('`%s` != `%s`' % (varName, assertedValue))
            return False

    def makeInputJson(self):
        """Makes the data to be sent to the taskgrader."""

        unittest.skip("makeInputJson must be overloaded.")

    def makeChecks(self):
        """Return the list of check resulsts."""

        unittest.skip("makeChecks must be overloaded.")

    def isCorrect(self):
        """Checks whether the results correspond to expectations."""

        checkList = self.makeChecks()
        good = len(filter(None, checkList))
        bad = len(checkList) - good

        if bad > 0:
            self.details['msg'] = 'Test %s failed, %d checks good, %d checks bad.' % (self.__class__.__name__, good, bad)
            return False
        else:
            self.details['msg'] = 'Test %s passed, %d checks good.' % (self.__class__.__name__, good)
            return True

    def shortDescription(self):
        """Return a short description of the test."""
        # Overload to have a better control
        return getattr(self, 'description', '')

    def runTest(self):
        """Run the test."""
        if self.__class__ == FullTestBase:
            self.skipTest("Base class")

        self.details = {}

        self.inputJson = self.makeInputJson()
        self.proc = subprocess.Popen([CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (self.procOut, self.procErr) = communicateWithTimeout(self.proc, 15, input=json.dumps(self.inputJson))
        self.details = {'stdout': self.procOut,
                'stderr': self.procErr,
                'returncode': self.proc.returncode,
                'good': [], # Will contain good assertions
                'bad': []}  # Will contain bad assertions
        try:
            self.outputJson = json.loads(self.procOut)
            self.details['validjson'] = True
        except:
            self.details['validjson'] = False
            self.details['errorDetails'] = self.details['stderr']
        self.result = self.isCorrect()
        if not self.result:
            self.assertTrue(self.details['validjson'], msg="Exception occured in taskgrader")
            self.details['errorDetails'] = str(self.details)
            self.assertTrue(self.result, msg="%s" % self.details['msg'])


class SanitizerCheckerTest(FullTestBase):
    """This test only sends a sanitizer and a checker to compile; the expected
    behavior is to have the taskgrader compile them and then exit successfully
    without evaluating any solution."""

    description = "sanitizer & checker test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['sanitizer']['exitCode']", 0),
            self.assertVariableEqual("outputJson['checker']['exitCode']", 0)
            ]

class BadSanitizerTest(FullTestBase):
    """This test sends a bad sanitizer which cannot compile; the taskgrader is
    expected to exit with an error after being unable to compile the
    sanitizer."""

    description = "invalid sanitizer test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': [],
            'sanitizer': '@testBadProgram',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 1),
            ]

class BadCheckerTest(FullTestBase):
    """This test sends a bad checker which cannot compile; the taskgrader is
    expected to exit with an error after being unable to compile the
    checker."""

    description = "invalid checker test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testBadProgram',
            'solutions': [],
            'executions': []
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 1)
            ]

class GenerationSingleTest(FullTestBase):
    """This test uses a simple generator, and checks whether it is executed
    successfully."""

    description = "simple generator test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': ['@testGenerator1'],
            'generations': ['@testGenerationSingle'],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['generators'][0]['compilationExecution']['exitCode']", 0),
            self.assertVariableEqual("outputJson['generations'][0]['generatorExecution']['exitCode']", 0)
            ]

class GenerationCasesTest(FullTestBase):
    """This test uses the "testCases" feature: it generates an input test file
    and the expected output with a couple generator + output generator."""

    description = "generation per case test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': ['@testGenerator2', '@testGenerator2out'],
            'generations': ['@testGenerationCases'],
            'extraTests': [],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [],
            'executions': []
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['generators'][0]['compilationExecution']['exitCode']", 0),
            self.assertVariableEqual("outputJson['generators'][1]['compilationExecution']['exitCode']", 0),
            self.assertVariableEqual("outputJson['generations'][0]['generatorExecution']['exitCode']", 0),
            self.assertVariableEqual("outputJson['generations'][0]['outputGeneratorExecution']['exitCode']", 0),
            self.assertVariableEqual("outputJson['generations'][0]['generatorExecution']['stdout']['data']", "20"),
            self.assertVariableEqual("outputJson['generations'][0]['outputGeneratorExecution']['stdout']['data']", "40"),
            ]

class SolutionSimpleBase(FullTestBase):
    """This test tries a simple solution execution, with one test file, and
    checks the checker output."""

    _dependencies = []
    _solution = None
    _execution = None

    def makeInputJson(self):
        if not (self._dependencies and self._solution and self._execution):
            self.skipTest("No solution defined.")

        for d in self._dependencies:
            self.assertTrue(programExists(d), msg="Dependency `%s` missing." % d)

        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': [self._solution],
            'executions': [self._execution]
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['checker']['stdout']['data']", "100")
            ]

class SolutionSimpleC(SolutionSimpleBase):
    description = "C test"
    _dependencies = ['gcc']
    _solution = '@testSolutionC'
    _execution = '@testExecutionC'

class SolutionSimpleCpp(SolutionSimpleBase):
    description = "C++ test"
    _dependencies = ['g++']
    _solution = '@testSolutionCpp'
    _execution = '@testExecutionCpp'

class SolutionSimpleJava(SolutionSimpleBase):
    description = "Java test"
    _dependencies = ['gcj']
    _solution = '@testSolutionJava'
    _execution = '@testExecutionJava'

@unittest.skip('test not working') # TODO :: fix
class SolutionSimpleJavascool(SolutionSimpleBase):
    description = "Javascool test"
    _dependencies = ['gcj']
    _solution = '@testSolutionJavascool'
    _execution = '@testExecutionJavascool'

class SolutionSimpleJs(SolutionSimpleBase):
    description = "Node.js test"
    _dependencies = ['nodejs']
    _solution = '@testSolutionJs'
    _execution = '@testExecutionJs'

class SolutionSimpleOcaml(SolutionSimpleBase):
    description = "OCaml test"
    _dependencies = ['ocamlopt']
    _solution = '@testSolutionOcaml'
    _execution = '@testExecutionOcaml'

class SolutionSimplePascal(SolutionSimpleBase):
    description = "Pascal test"
    _dependencies = ['fpc']
    _solution = '@testSolutionPascal'
    _execution = '@testExecutionPascal'

class SolutionSimplePhp(SolutionSimpleBase):
    description = "PHP test"
    _dependencies = ['php5']
    _solution = '@testSolutionPhp'
    _execution = '@testExecutionPhp'

class SolutionSimplePython(SolutionSimpleBase):
    description = "Python2.7 test"
    _dependencies = ['python2.7']
    _solution = '@testSolutionPython'
    _execution = '@testExecutionPython'

class SolutionSimpleShell(SolutionSimpleBase):
    description = "shell script test"
    _solution = '@testSolutionShell'
    _execution = '@testExecutionShell'

class SolutionInvalidTest(FullTestBase):
    """This test tries an invalid solution (giving a wrong result), with one
    test file, and checks the checker output."""

    description = "wrong solution test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionInvalid'],
            'executions': ['@testExecutionInvalid']
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['checker']['stdout']['data']", "0")
            ]

class SolutionUncompTest(FullTestBase):
    """This test tries a bad solution which cannot be compiled."""

    description = "uncompilable test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionUncomp'],
            'executions': ['@testExecutionUncomp']
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['solutions'][0]['compilationExecution']['exitCode']", 1)
            ]

@unittest.skip('test not working') # TODO :: fix
class SolutionMemoverflowTest(FullTestBase):
    """This test tries a solution using more memory than the allowed limit."""

    description = "memory limit test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionMemoverflow'],
            'executions': ['@testExecutionMemoverflow']
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitCode']", 1),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitSig']", 11)
            ]

class SolutionTimeoutTest(FullTestBase):
    """This test tries a solution using more time than the allowed limit."""

    description = "wall time & cpu time limit test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionTimeout1', '@testSolutionTimeout2'],
            'executions': ['@testExecutionTimeout1', '@testExecutionTimeout2']
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitCode']", 1),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['execution']['exitSig']", 137),
            self.assertVariableEqual("outputJson['executions'][1]['testsReports'][0]['execution']['exitCode']", 1),
            self.assertVariableEqual("outputJson['executions'][1]['testsReports'][0]['execution']['exitSig']", 137)
            ]

class SolutionChangingTest(FullTestBase):
    """This test tries executing a solution (whose output changes) twice and
    checks whether its result has correctly been cached."""

    description = "cache test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionChanging'],
            'executions': ['@testExecutionChanging1', '@testExecutionChanging2']
            }

    def makeChecks(self):
        checks = [
            self.assertVariableEqual("proc.returncode", 0),
            ]
        try:
            output1 = self.outputJson['executions'][0]['testsReports'][0]['execution']['stdout']['data']
        except:
            self.details['bad'].append("can't get output from first execution")
            checks.append(False)
            return checks
        try:
            output2 = self.outputJson['executions'][1]['testsReports'][0]['execution']['stdout']['data']
        except:
            self.details['bad'].append("can't get output from second execution")
            checks.append(False)
            return checks
        if output1 == output2:
            self.details['good'].append("output1 == output2")
        else:
            self.details['bad'].append("output1 != output2")
        checks.append(output1 == output2)
        return checks

class TestMultipleTest(FullTestBase):
    """This test tries a simple solution with multiple test files, and checks
    the solution and the checker output."""

    description = "multiple test cases & C solution test"

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'generators': [],
            'generations': [],
            'extraTests': ['@testExtraSimple1', '@testExtraSimple2', '@testExtraSimple3'],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionC'],
            'executions': ['@testExecutionC']
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 0),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['execution']['stdout']['data']", "60"),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][0]['checker']['stdout']['data']", "100"),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][1]['execution']['stdout']['data']", "90"),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][1]['checker']['stdout']['data']", "100"),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][2]['execution']['stdout']['data']", "384"),
            self.assertVariableEqual("outputJson['executions'][0]['testsReports'][2]['checker']['stdout']['data']", "100")
            ]

class TestRestrictPath(FullTestBase):
    """This test tries to load a file which is not in the paths allowed by
    restrictToPaths."""

    description = "allowed paths restriction test"

    def setUp(self):
        """Create a temporary file that we'll use as the test file."""
        (fd, self.tempfileName) = tempfile.mkstemp()
        open(self.tempfileName, 'w').write("2")

    def tearDown(self):
        """Delete the temporary file."""
        os.unlink(self.tempfileName)

    def makeInputJson(self):
        return {
            'rootPath': os.path.dirname(os.path.abspath(__file__)),
            'taskPath': '$ROOT_PATH',
            'restrictToPaths': ['$ROOT_PATH'],
            'generators': [],
            'generations': [],
            'extraTests': [{"name": "notinrestrict.in", "path": self.tempfileName}],
            'sanitizer': '@testSanitizer',
            'checker': '@testChecker',
            'solutions': ['@testSolutionC'],
            'executions': ['@testExecutionC']
            }

    def makeChecks(self):
        return [
            self.assertVariableEqual("proc.returncode", 1),
            ]


class TaskgraderTestResult(unittest.TextTestResult):
    """A class to display results from the taskgrader test."""

    def getDescription(self, test):
        # Overload to show only the description
        shortDescr = test.shortDescription()
        if self.descriptions and shortDescr:
            return shortDescr
        else:
            return str(test)

    def printErrorList(self, flavour, errors):
        # Overload for a more condensed view and to show errorDetails
        for test, err in errors:
            self.stream.writeln("%s on %s: %s" % (flavour, self.getDescription(test), err))
            if self.showAll and test.details.get('errorDetails', None):
                self.stream.writeln("Details: %s" % test.details['errorDetails'])

    def _exc_info_to_string(self, err, test):
        # Overload to remove the traceback if non-verbose
        e, v, t = err
        return ''.join(traceback.format_exception(e, v, None)).strip()


class TaskgraderTestRunner(unittest.TextTestRunner):
    """A class to run tests and display the results with
    TaskgraderTestResult."""

    # We make a class to use as argument to unittest.main
    # Else we have to make an instance, and we'd lose the options that
    # unittest.main would pass to the TestRunner

    def __init__(self, **kwargs):
        kwargs['resultclass'] = TaskgraderTestResult
        unittest.TextTestRunner.__init__(self, **kwargs)


if __name__ == '__main__':
    # Start all tests
    unittest.main(testRunner=TaskgraderTestRunner)
