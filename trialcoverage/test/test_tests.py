from twisted.trial import unittest

from pyutil import fileutil

from twisted.scripts import trial

import os, sys

from mock import Mock

from trialcoverage import trialcoverage

class T(unittest.TestCase):
    def setUp(self):
        trialcoverage.cov.stop()
        fileutil.remove_if_possible(trialcoverage.COVERAGE_FNAME)

    def test_basic_test(self):
        pkgname='fakepackage4'
        modname='fakemodule4'
        modcontents='\n\
def foofunc():\n\
    x=1\n\
    y=x\n\
'
        testcontents='\n\
from twisted.trial import unittest\n\
from %s import %s\n\
class T(unittest.TestCase):\n\
    def test_thing(self):\n\
        %s.foofunc()\n\
' % (pkgname, modname, modname)

        mockstdout = Mock()
        realstdout=sys.stdout
        sys.stdout = mockstdout
        mockstderr = Mock()
        realstderr=sys.stderr
        sys.stderr = mockstderr
        something = None
        try:
            fileutil.make_dirs(pkgname)
            fileutil.write_file(os.path.join(pkgname, '__init__.py'), '')
            fileutil.write_file(os.path.join(pkgname, modname+'.py'), modcontents)
            fileutil.make_dirs(os.path.join(pkgname, 'test'))
            fileutil.write_file(os.path.join(pkgname, 'test', '__init__.py'), '')
            fileutil.write_file(os.path.join(pkgname, 'test', 'test_'+modname+'.py'), testcontents)
            sys.path.append(os.getcwd())
            trialcoverage.init_paths()
            trialcoverage.start_coverage()

            config = trial.Options()
            config.parseOptions(['--reporter', 'bwverbose-coverage', '%s.test' % pkgname])
            trial._initialDebugSetup(config)
            trialRunner = trial._makeRunner(config)
            suite = trial._getSuite(config)
            something = trialRunner.run(suite)

        finally:
            sys.stdout = realstdout
            sys.stderr = realstderr
            if sys.modules.has_key(pkgname):
                del sys.modules[pkgname]
            fileutil.rm_dir(pkgname)
            # print something, type(something)
            # print dir(something)

    def UNFINISHED_test_successive_different_code(self):
        pkgname='fakepackage4'
        modname='fakemodule4'
        modcontents=''

        realstderr=sys.stderr
        mockstderr = Mock()
        sys.stderr = mockstderr
        try:
            fileutil.make_dirs(pkgname)
            fileutil.write_file(os.path.join(pkgname, '__init__.py'), "")
            fileutil.write_file(os.path.join(pkgname, modname+'.py'), modcontents)
            sys.path.append(os.getcwd())
            trialcoverage.import_all_python_files([pkgname])
            return mockstderr
        finally:
            sys.stderr = realstderr
            if sys.modules.has_key(pkgname):
                del sys.modules[pkgname]
            fileutil.rm_dir(pkgname)
