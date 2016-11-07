#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: Module for logging formatter for colored output via console
"""

# Standard modules
import logging
# import os.path
# import sys
import copy

# Third party modules
import termcolor
from termcolor import colored

__version__ = '0.1.0'

class ColoredFormatter(logging.Formatter):
    """A logging formatter class for emitting colored console output."""

    level_color = {
        'DEBUG':    None,
        'INFO':     {'color': 'green'}
        'WARNING':  {'color': 'yellow'},
        'ERROR':    {'color': 'red', 'attrs': ['bold']},
        'CRITICAL': {'bg_color': 'on_red'},
    }

    # -------------------------------------------------------------------------
    def __init__(self, fmt=None, datefmt=None):
        """
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default. Allow for specialized date formatting with the optional
        datefmt argument (if omitted, you get the ISO8601 format).
        """

        logging.Formatter.__init__(self, fmt, datefmt)

    # -----------------------------------------------------------
    @classmethod
    def set_color_value(cls, level, value):
        if not isinstance(level, dict):
            cls.level_color[level] = None

    # -----------------------------------------------------------
    @property
    def color_debug(self):
        """The color used to output debug messages."""
        return self.level_color['DEBUG']



# =============================================================================

if __name__ == "__main__":
    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
