#!/usr/bin/env python

# trialcoverage -- plugin to integrate Twisted trial with Ned Batchelder's coverage.py
#
# Author: Brian Warner
# Packaged by: Zooko Wilcox-O'Hearn
# Thanks to: Jonathan Lange
#
# See README.txt for licensing information.

import os, re, sys

try:
    from ez_setup import use_setuptools
except ImportError:
    pass
else:
    use_setuptools(download_delay=0)

from setuptools import find_packages, setup

trove_classifiers=[
    "Development Status :: 4 - Beta",
    "License :: OSI Approved :: GNU General Public License (GPL)",
    "License :: DFSG approved",
    "License :: OSI Approved :: BSD License",
    "License :: Other/Proprietary License",
    "Intended Audience :: Developers",
    "Operating System :: OS Independent",
    "Natural Language :: English",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 2.4",
    "Programming Language :: Python :: 2.5",
    "Programming Language :: Python :: 2.6",
    "Topic :: Software Development :: Libraries",
    ]

PKG='trialcoverage'
VERSIONFILE = os.path.join(PKG, "_version.py")
verstr = "unknown"
try:
    verstrline = open(VERSIONFILE, "rt").read()
except EnvironmentError:
    pass # Okay, there is no version file.
else:
    VSRE = r"^verstr = ['\"]([^'\"]*)['\"]"
    mo = re.search(VSRE, verstrline, re.M)
    if mo:
        verstr = mo.group(1)
    else:
        print "unable to find version in %s" % (VERSIONFILE,)
        raise RuntimeError("if %s.py exists, it must be well-formed" % (VERSIONFILE,))

setup_requires = []

data_fnames=[ 'COPYING.SPL.txt', 'COPYING.GPL', 'COPYING.TGPPL.html', 'README.txt' ]

# In case we are building for a .deb with stdeb's sdist_dsc command, we put the
# docs in "share/doc/python-$PKG".
doc_loc = "share/doc/" + PKG
data_files = [(doc_loc, data_fnames)]

# The twisted plugin has to go into twisted/plugins.
data_files.append((os.path.join('twisted', 'plugins'), [os.path.join('twisted', 'plugins', 'trialcoveragereporterplugin.py')]))

setup(name=PKG,
      version=verstr,
      description="a plugin to integrate Twisted trial with Ned Batchelder's coverage.py",
      author='Brian Warner',
      author_email='zooko@zooko.com',
      url='http://tahoe-lafs.org/trac/' + PKG,
      license='BSD', # see README.txt for details -- there are also alternative licences
      packages=find_packages(),
      include_package_data=True,
      setup_requires=setup_requires,
      classifiers=trove_classifiers,
      zip_safe=False, # I prefer unzipped for easier access.
      install_requires=['coverage>=3.4a1', 'pyutil>=1.6.0', 'setuptools'],
      tests_require=['mock', 'setuptools_trial >= 0.5'],
      data_files=data_files,
      test_suite='trialcoverage.test',
      )
