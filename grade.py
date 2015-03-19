#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2015 France-IOI, MIT license
#
# http://opensource.org/licenses/MIT



import getopt
# Usual imports
import glob, hashlib, json, os, random, shlex, shutil, sys, subprocess

# Taskgrader path
CFG_TASKGRADER = '/home/michel/franceioi/taskgrader/taskgrader.py'
# Default solution compilation and execution parameters
CFG_EXECPARAMS = {'timeLimitMs': 60000,
                  'memoryLimitKb': 128*1024,
                  'useCache': True,
                  'stdoutTruncateKb': -1,
                  'stderrTruncateKb': -1,
                  'getFiles': []}
# Languages supported, file extension -> language
CFG_LANGUAGES = {'.c': 'c',
                 '.cpp': 'cpp',
                 '.py': 'py',
                 '.ml': 'ocaml',
                 '.java': 'java',
                 '.pas': 'pascal',
                 '.sh': 'sh',
                 '': 'sh'}


if __name__ == '__main__':
    execParams = {}
    execParams.update(CFG_EXECPARAMS)
    debug = False

    # We default the task path to the current directory if there's a defaultParams in it
    if os.path.isfile('defaultParams.json'):
        taskPath = os.getcwd()
    else:
        taskPath = None

    # Read command line options
    try:
        (opts, files) = getopt.getopt(sys.argv[1:], 'dm:t:p:', ['debug', 'memory-limit=', 'time-limit=', 'task-path='])
    except getopt.GetoptError as err:
        print str(err)
        sys.exit(1)
    for (opt, arg) in opts:
        if opt in ['-d', '--debug']:
            debug = True
        elif opt in ['-m', '--memory-limit']:
            execParams['memoryLimitKb'] = int(arg)
        elif opt in ['-t', '--time-limit']:
            execParams['timeLimitMs'] = int(arg)
        elif opt in ['-p', '--task-path']:
            taskPath = arg

    if not taskPath or not os.path.isfile(os.path.join(taskPath, 'defaultParams.json')):
        print "Current directory is not a task and no task path given. Aborting."
        sys.exit(1)

    print "Running task in %s" % taskPath

    defaultParams = json.load(open(os.path.join(taskPath, 'defaultParams.json'), 'r'))

    solId = 0
    testSolutions = []
    testExecutions = []
    # We add the parameters for each solution file given
    for f in files:
        filePath = os.path.join(os.getcwd(), f)
        solName = os.path.basename(f)
        solId += 1

        # Auto-detect language from extension
        (r, ext) = os.path.splitext(f)
        lang = CFG_LANGUAGES[ext]

        print "Adding solution %s, language %s" % (f, lang)

        testSolutions.append({
            'id': 'sol%d-%s' % (solId, solName),
            'compilationDescr': {
                'language': lang,
                'files': [{'name': os.path.basename(f),
                           'path': filePath}],
                'dependencies': '@defaultDependencies-' + lang},
            'compilationExecution': execParams})

        testExecutions.append({
            'id': 'exec%d-%s' % (solId, solName),
            'idSolution': 'sol%d-%s' % (solId, solName),
            'filterTests': '@defaultFilterTests-' + lang,
            'runExecution': execParams})

    # Final evaluation JSON to be given to the taskgrader
    testEvaluation = {
        'rootPath': defaultParams['rootPath'],
        'taskPath': taskPath,
        'generators': ['@defaultGenerator'],
        'generations': ['@defaultGeneration'],
        'extraTests': '@defaultExtraTests',
        'sanitizer': '@defaultSanitizer',
        'checker': '@defaultChecker',
        'solutions': testSolutions,
        'executions': testExecutions}

    if debug:
        print ''
        print '* JSON sent to taskgrader:'
        print json.dumps(testEvaluation)

    # Send to taskgrader
    print ''
    print '* Output from taskgrader'
    proc = subprocess.Popen(['/usr/bin/python', CFG_TASKGRADER], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    (procOut, procErr) = proc.communicate(input=json.dumps(testEvaluation))
    print ''

    print '* Results'
    resultJson = json.loads(procOut)
    for execution in resultJson['executions']:
        print ' * Execution %s:' % execution['name']
        for report in execution['testsReports']:
            if report.has_key('checker'):
                # Everything was executed
                print 'Solution executed successfully. Checker report:'
                print report['checker']['stdout']['data']
            elif report.has_key('solution'):
                # Solution error
                print 'Solution returned an error. Solution report:'
                print json.dumps(report['solution'])
            else:
                # Sanitizer error
                print 'Test rejected by sanitizer. Sanitizer report:'
                print json.dumps(report['sanitizer'])
    if debug:
        print ''
        print '* Full report:'
        print json.dumps(resultJson)
