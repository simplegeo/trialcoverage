"""
A Trial IReporter plugin that gathers coverage.py code-coverage information.

Once this plugin is installed, trial can be invoked a new --reporter option:

  trial --reporter-bwverbose-coverage ARGS

Once such a test run has finished, there will be a .coverage file in the
top-level directory. This file can be turned into a directory of .html files
(with index.html as the starting point) by running:

 coverage html -d OUTPUTDIR --include=PREFIX1/*,PREFIX2/*,..

Before using this, you need to install the 'coverage' package, which will
provide an executable tool named 'coverage' ('python-coverage' on Ubuntu) as
well as an importable library. 'coverage report' will produce a basic text
summary of the coverage data.
"""

import errno, os, shutil, sys

from pyutil import fileutil
from pyutil.assertutil import precondition

import twisted.trial.reporter

import setuptools

class SummaryTextParseError(Exception): pass

# These plugins are registered via twisted/plugins/trialcoveragereporterplugin.py .
# See the notes there for an explanation of how that works.

# Some notes about how trial Reporters are used:
# * Reporters don't really get told about the suite starting and stopping.
# * The Reporter class is imported before the test classes are.
# * The test classes are imported before the Reporter is created. To get
#   control earlier than that requires modifying twisted/scripts/trial.py
# * Then Reporter.__init__ is called.
# * Then tests run, calling things like write() and addSuccess(). Each test is
#   framed by a startTest/stopTest call.
# * Then the results are emitted, calling things like printErrors,
#   printSummary, and wasSuccessful.
# So for code-coverage (not including import), start in __init__ and finish
# in printSummary. To include import, we have to start in our own import and
# finish in printSummary.

import coverage

from coverage.report import Reporter as CoverageReporter
from coverage.summary import SummaryReporter as CoverageSummaryReporter
import coverage.summary

def import_all_python_files(packages):
    precondition(not isinstance(packages, basestring), "packages is required to be a sequence.", packages=packages) # common mistake
    for package in packages:
        packagedir = '/'.join(package.split('.'))

        for (dirpath, dirnames, filenames) in os.walk(packagedir):
            for filename in (filename for filename in filenames if filename.endswith('.py')):
                dirs = dirpath.split("/")
                if filename != "__init__.py":
                    dirs.append(filename[:-3])
                import_str = "%s" % ".".join(dirs)
                if import_str not in ("setup", __name__):
                    try:
                        __import__(import_str)
                    except ImportError, le:
                        if 'No module named' in str(le):
                            # Oh whoops I guess that Python file we found isn't a module of this package. Nevermind.
                            pass
                        else:
                            sys.stderr.write("WARNING, importing %s resulted in an ImportError %s. I'm ignoring this ImportError, as I was trying to import it only for the purpose of marking its import-time statements as covered for code-coverage accounting purposes.\n" % (import_str, le,))
                    except Exception, le:
                        sys.stderr.write("WARNING, importing %s resulted in an Exception %s. I'm ignoring this Exception, as I was trying to import it only for the purpose of marking its import-time statements as covered for code-coverage accounting purposes.\n" % (import_str, le,))

def move_if_present(src, dst):
    try:
        shutil.move(src, dst)
    except EnvironmentError, le:
        # Ignore "No such file or directory", re-raise any other exception.
        if (le.args[0] != 2 and le.args[0] != 3) or (le.args[0] != errno.ENOENT):
            raise

def copy_if_present(src, dst):
    try:
        shutil.copy2(src, dst)
    except EnvironmentError, le:
        # Ignore "No such file or directory", re-raise any other exception.
        if (le.args[0] != 2 and le.args[0] != 3) or (le.args[0] != errno.ENOENT):
            raise

def parse_out_unc_and_part(summarytxt):
    for line in summarytxt.split('\n'):
        if line.startswith('Name'):
            linesplit = line.split()
            missix = linesplit.index('Miss')
            try:
                brpartix = linesplit.index('BrPart')
            except ValueError, le:
                sys.stderr.write("ERROR, this tool requires a version of coverage.py new enough to report branch coverage, which was introduced in coverage.py v3.2.\n")
                le.args = tuple(le.args + (linesplit,))
                raise

        if line.startswith('TOTAL'):
            linesplit = line.split()
            return (int(linesplit[missix]), int(linesplit[brpartix]))
    raise SummaryTextParseError("Control shouldn't have reached here because there should have been a line that started with 'TOTAL'. The full summary text was %r." % (summarytxt,))

class ProgressionReporter(CoverageReporter):
    """A reporter for testing whether your coverage is improving or degrading. """

    def __init__(self, coverage, show_missing=False, ignore_errors=False):
        super(ProgressionReporter, self).__init__(coverage, ignore_errors)
        self.summary_reporter = CoverageSummaryReporter(coverage, show_missing=show_missing, ignore_errors=ignore_errors)

    def coverage_progressed(self):
        """ Returns 0 if coverage has regressed, 1 if there was no
        existing best-coverage summary, 2 if coverage is the same as
        the existing best-coverage summary, 3 if coverage is improved
        compared to the existing best-coverage summary. """
        if not hasattr(self, 'bestunc'):
            return 1

        if (self.curtot == self.besttot) and (self.curunc == self.bestunc):
            return 2

        if (self.curtot <= self.besttot) and (self.curunc <= self.bestunc):
            return 3
        else:
            return 0

    def report(self, morfs, omit=None, outfile=None, include=None):
        """Writes a report summarizing progression/regression."""
        # First we use our summary_reporter to generate a text summary of the current version.
        if outfile is None:
            outfile = SUMMARY_FNAME
        outfileobj = open(outfile, "w")
        self.summary_reporter.report(morfs, omit=omit, outfile=outfileobj, include=include)
        outfileobj.close()

        self.curunc, self.curpart = parse_out_unc_and_part(fileutil.read_file(SUMMARY_FNAME, mode='rU'))
        self.curtot = self.curunc + self.curpart

        # Then we see if there is a previous best version and if so what its count of uncovered and partially covered lines was.
        try:
            self.bestunc, self.bestpart = parse_out_unc_and_part(fileutil.read_file(BEST_SUMMARY_FNAME, mode='rU'))
        except IOError, le:
            # Ignore "No such file or directory", report and ignore any other error.
            if (le.args[0] != 2 and le.args[0] != 3) or (le.args[0] != errno.ENOENT):
                sys.stderr.write("WARNING, got unexpected IOError from attempt to read best-ever summary file: %s\n" % (le,))
            pass
        except SummaryTextParseError, le:
            sys.stderr.write("WARNING, got unexpected SummaryTextParseError from attempt to read best-ever summary file: %s\n" % (le,))
            pass
        else:
            self.besttot = (self.bestunc + self.bestpart)

        progression = self.coverage_progressed()
        sys.stdout.write("\n"+"-"*79+"\n")
        sys.stdout.write("code coverage summary\n")
        if progression == 0:
            sys.stdout.write("WARNING code coverage regression\n")
            sys.stdout.write("Previous best coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.besttot, self.bestunc, self.bestpart))
            sys.stdout.write("Current coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.curtot, self.curunc, self.curpart))
            return progression

        if progression == 1:
            sys.stdout.write("There was no previous best code-coverage summary found.\n")
            sys.stdout.write("Current coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.curtot, self.curunc, self.curpart))
        elif progression == 2:
            sys.stdout.write("code coverage totals unchanged\n")
            sys.stdout.write("Previous best coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.besttot, self.bestunc, self.bestpart))
            sys.stdout.write("Current coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.curtot, self.curunc, self.curpart))
        elif progression == 3:
            sys.stdout.write("code coverage improvement!\n")
            sys.stdout.write("Previous best coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.besttot, self.bestunc, self.bestpart))
            sys.stdout.write("Current coverage left %d total lines untested (%d lines uncovered and %d lines partially covered).\n" % (self.curtot, self.curunc, self.curpart))

        shutil.copy2(COVERAGE_FNAME, BEST_COVERAGE_FNAME)
        shutil.copy2(SUMMARY_FNAME, BEST_SUMMARY_FNAME)
        copy_if_present(VERSION_STAMP_FNAME, BEST_VERSION_STAMP_FNAME)
        return progression

class CoverageTextReporter(twisted.trial.reporter.VerboseTextReporter):
    def __init__(self, *args, **kwargs):
        global cov, packages
        twisted.trial.reporter.VerboseTextReporter.__init__(self, *args, **kwargs)
        self.pr = None
        import_all_python_files(packages)
        cov.stop() # It was started when this module was imported.
        cov.save()

    def startTest(self, test):
        res = twisted.trial.reporter.VerboseTextReporter.startTest(self, test)
        cov.start()
        # print "%s.startTest(%s) self.collector._collectors: %s" % (self, test, cov.collector._collectors)
        return res

    def stopTest(self, test):
        res = twisted.trial.reporter.VerboseTextReporter.stopTest(self, test)
        # print "%s.stopTest(%s) self.collector._collectors: %s" % (self, test, cov.collector._collectors)
        cov.stop()
        cov.save()
        return res

    def stop_coverage(self):
        sys.stdout.write("Coverage results written to %s\n" % (COVERAGE_FNAME,))
        assert self.pr is None, self.pr
        self.pr = ProgressionReporter(cov)
        self.pr.report(None)

    def printSummary(self):
        # for twisted-2.5.x
        self.stop_coverage()
        return twisted.trial.reporter.VerboseTextReporter.printSummary(self)

    def done(self):
        # for twisted-8.x
        self.stop_coverage()
        return twisted.trial.reporter.VerboseTextReporter.done(self)

    def wasSuccessful(self):
        return super(CoverageTextReporter, self).wasSuccessful() and self.pr.coverage_progressed()

def init_paths():
    global RES_DIRNAME, RES_FULLDIRNAME, COVERAGE_FNAME, BEST_DIRNAME, BEST_COVERAGE_FNAME, SUMMARY_FNAME, BEST_SUMMARY_FNAME, VERSION_STAMP_FNAME, BEST_VERSION_STAMP_FNAME

    # We keep our notes about previous best code-coverage results in a
    # folder named ".coverage-results".
    RES_DIRNAME='.coverage-results'
    RES_FULLDIRNAME=os.path.realpath(os.path.abspath(os.path.expanduser(RES_DIRNAME)))
    fileutil.make_dirs(RES_FULLDIRNAME)
    COVERAGE_FNAME=os.path.join(os.path.abspath(os.getcwd()), '.coverage')
    BEST_DIRNAME=os.path.join(RES_FULLDIRNAME, 'best')
    fileutil.make_dirs(BEST_DIRNAME)
    BEST_COVERAGE_FNAME=os.path.join(BEST_DIRNAME, '.coverage')
    SUMMARY_FNAME=os.path.join(RES_FULLDIRNAME, 'summary.txt')
    BEST_SUMMARY_FNAME=os.path.join(BEST_DIRNAME, 'summary.txt')
    VERSION_STAMP_FNAME=os.path.join(RES_FULLDIRNAME, 'version-stamp.txt')
    BEST_VERSION_STAMP_FNAME=os.path.join(BEST_DIRNAME, 'version-stamp.txt')

def start_coverage():
    global cov, packages
    packages = setuptools.find_packages('.')
    includes = [os.path.join(pkg.replace('.', os.sep), '*') for pkg in packages]
    cov = coverage.coverage(include=includes, branch=True, auto_data=True)
    # poke the internals of coverage to work-around this issue:
    # http://bitbucket.org/ned/coveragepy/issue/71/atexit-handler-results-in-exceptions-from-half-torn-down
    cov.atexit_registered = True
    cov.start()


# As noted above, we have to do this at import time because trial
# doesn't call the reporter before importing the test files, and we
# want to turn on coverage before any of the package files (including
# its test files) get imported.
init_paths()
start_coverage()
