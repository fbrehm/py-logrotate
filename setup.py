#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.6.1
@summary: setup for pylogrotate
'''

import os
import sys
import re
import datetime
import textwrap

# Third party modules
import six

from setuptools import setup

setup(
    name='pylogrotate',
    version='0.6.0',
    description='rotates and compress system logs',
    author='Frank Brehm',
    author_email='frank@brehm-online.com',
    url='http://svn.brehm-online.com/svn/my-stuff/python/PyLogrotate/',
    packages=['LogRotate'],
    scripts = [
        'bin/plogrotate',
    ],
)



#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
