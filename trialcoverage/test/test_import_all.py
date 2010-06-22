from twisted.trial import unittest

from pyutil import fileutil

from trialcoverage import trialcoverage

import os, sys

from mock import Mock

class T(unittest.TestCase):
    def _help_test_ignore_error(self, pkgname, modname, isrealpackage, modcontents):
        """ I return the mockstderr object so you can check what the
        code under test said to sys.stderr. """
        realstderr=sys.stderr
        mockstderr = Mock()
        sys.stderr = mockstderr
        try:
            fileutil.make_dirs(pkgname)
            if isrealpackage:
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

    def test_ignore_import_error_not_a_package(self):
        """
        Sometimes there is a Python file which is not a module in this
        package, but is just a Python file. For example the developers
        may invoke it as a script from the command-line but it can't
        be imported as a member of a package.

        Since the only reason we are trying to import it is to account
        for its import-time statements (such as def, class, and
        import) in our code coverage results, we should just silently
        ignore these ImportErrors.
        """
        mockstderr = self._help_test_ignore_error('fakepackage', 'fakemodule', False, "print 'Yellow Whirled'")
        self.failIf(mockstderr.method_calls, mockstderr.method_calls)

    def test_ignore_import_error(self):
        """
        Sometimes there is a Python file which raises ImportError for
        some reason.

        Since the only reason we are trying to import it is to account
        for its import-time statements (such as def, class, and
        import) in our code coverage results, we should just report
        these ImportErrors to stderr and carry on.
        """
        mockstderr = self._help_test_ignore_error('otherfakepackage', 'otherfakemodule', True, "raise ImportError('Yellow Whirled')")
        self.failUnlessEqual(mockstderr.method_calls[0][0], 'write')
        self.failUnless('resulted in an ImportError' in mockstderr.method_calls[0][1][0], mockstderr.method_calls[0][1][0])

    def test_ignore_any_exception_on_import(self):
        """
        Sometimes there is a Python file which raises some exception
        when imported.

        Since the only reason we are trying to import it is to account
        for its import-time statements (such as def, class, and
        import) in our code coverage results, we should just report
        these Exceptions to stderr and carry on.
        """
        mockstderr = self._help_test_ignore_error('fakepackage3', 'fakemodule3', True, "raise Exception('whoo')")
        self.failUnlessEqual(mockstderr.method_calls[0][0], 'write')
        self.failUnless('resulted in an Exception' in mockstderr.method_calls[0][1][0], mockstderr.method_calls[0][1][0])
