#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: Module for logging formatter for colored output via console
"""

from __future__ import print_function

# Standard modules
import logging
# import os.path
# import sys
import copy

# Third party modules
import termcolor
from termcolor import colored

__version__ = '0.2.0'


# =============================================================================
class Colorer(object):

    valid_textcolors = (
        'grey', 'red', 'green', 'yellow',
        'blue', 'magenta', 'cyan', 'white',)

    valid_bgcolors = (
        'on_grey', 'on_red', 'on_green', 'on_yellow',
        'on_blue', 'on_magenta', 'on_cyan', 'on_white',
    )

    valid_attrs = (
        'bold', 'dark', 'underline', 'blink', 'reverse', 'concealed',
    )


    # -------------------------------------------------------------------------
    def __init__(self, text_color=None, bg_color=None, attrs=None):

        self._text_color = None
        self._bg_color = None
        self.attrs = set()

        if (text_color and bg_color is None and
                str(text_color).lower().strip() in self.valid_bgcolors):
            self.bg_color = text_color
        else:
            self.text_color = text_color
            self.bg_color = bg_color

        if attrs is not None:
            if isinstance(attrs, str):
                self.set_attr(attrs)
            elif isinstance(attrs, (list, tuple, set)):
                for attr in attrs:
                    self.set_attr(attr)
            elif isinstance(attrs, dict):
                for attr in attrs.keys():
                    self.set_attr(attr)
            else:
                msg = "Invalid type %r of attributes %r." % (
                    attrs.__class__.__name__, attrs)
                raise TypeError(msg)

    # -----------------------------------------------------------
    @property
    def text_color(self):
        "The current text (foreground) color."
        return self._text_color

    @text_color.setter
    def text_color(self, value):
        if value is None:
            self._text_color = None
            return
        v = str(value).lower().strip()
        if v not in self.valid_textcolors:
            msg = "Invalid text (foreground) color %r." % (value)
            raise ValueError(msg)
        self._text_color = v

    # -----------------------------------------------------------
    @property
    def bg_color(self):
        "The current background color."
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value):
        if value is None:
            self._bg_color = None
            return
        v = str(value).lower().strip()
        if v not in self.valid_bgcolors:
            msg = "Invalid background color %r." % (value)
            raise ValueError(msg)
        self._bg_color = v

    # -------------------------------------------------------------------------
    def set_attr(self, value):

        v = str(value).lower().strip()
        if v not in self.valid_attrs:
            msg = "Invalid color attribute %r." % (value)
            raise ValueError(msg)
        self.attrs.add(v)

    # -------------------------------------------------------------------------
    def set_bold(self):
        self.set_attr('bold')

    # -------------------------------------------------------------------------
    def __str__(self):
        tokens = []
        if self.text_color:
            tokens.append(self.text_color)
        txt = self.text_color
        if self.bg_color:
            tokens.append(self.bg_color.replace('_', ' '))
        if self.attrs and len(self.attrs) > 0:
            tokens.append(' (' + ', '.join(self.attrs) + ')')
        return ' '.join(tokens)

    # -------------------------------------------------------------------------
    def __repr__(self):
        """Typecasting into a string for reproduction."""

        out = "<%s(" % (self.__class__.__name__)

        fields = []
        if self.text_color:
            fields.append("text_color=%r" % (self.text_color))
        if self.bg_color:
            fields.append("bg_color=%r" % (self.bg_color))
        if self.attrs and len(self.attrs) > 0:
            fields.append("attrs=%r" % (self.attrs))

        out += ", ".join(fields) + ")>"
        return out

    # -------------------------------------------------------------------------
    def __copy__(self):

        new = self.__class__(
            text_color=self.text_color,
            bg_color=self.bg_color,
            attrs=self.attrs)
        return new

    # -------------------------------------------------------------------------
    def coloring(self, text):
        return colored(
            text, color=self.text_color, on_color=self.bg_color, attrs=self.attrs)

    # -------------------------------------------------------------------------
    def cprint(self, text, **kwargs):
        print(self.coloring(text), **kwargs)

# =============================================================================
class ColoredFormatter(logging.Formatter):
    """A logging formatter class for emitting colored console output."""

    level_color = {
        'DEBUG':    None,
        'INFO':     Colorer('green'),
        'WARNING':  Colorer('yellow'),
        'ERROR':    Colorer('red', attrs='bold'),
        'CRITICAL': Colorer(bg_color='on_red', attrs='bold'),
    }
    bold = Colorer(attrs='bold')

    # -------------------------------------------------------------------------
    def __init__(self, fmt=None, datefmt=None, dark=False):
        """
        Initialize the formatter with specified format strings.

        Initialize the formatter either with the specified format string, or a
        default. Allow for specialized date formatting with the optional
        datefmt argument (if omitted, you get the ISO8601 format).
        """

        logging.Formatter.__init__(self, fmt, datefmt)
        if dark:
            # changing the default colors to "dark" because the xterm plugin
            # for Jenkins cannot use bright colors
            # see: http://stackoverflow.com/a/28071761
            self.level_color['DEBUG'] = Colorer('cyan', attrs='dark')
            self.level_color['INFO'] = Colorer('green', attrs='dark')
            self.level_color['WARNING'] = Colorer('yellow', attrs='dark')
            self.level_color['ERROR'] = Colorer('red', attrs='dark')

    # -----------------------------------------------------------
    @property
    def color_debug(self):
        """The color used to output debug messages."""
        return self.level_color['DEBUG']

    # -----------------------------------------------------------
    @property
    def color_info(self):
        """The color used to output info messages."""
        return self.LEVEL_COLOR['INFO']

    # -----------------------------------------------------------
    @property
    def color_warning(self):
        """The color used to output warning messages."""
        return self.LEVEL_COLOR['WARNING']

    # -----------------------------------------------------------
    @property
    def color_error(self):
        """The color used to output error messages."""
        return self.LEVEL_COLOR['ERROR']

    # -----------------------------------------------------------
    @property
    def color_critical(self):
        """The color used to output critical messages."""
        return self.LEVEL_COLOR['CRITICAL']

    # -------------------------------------------------------------------------
    @classmethod
    def set_color_value(cls, level, *values):
        colorer = Colorer(*values)
        cls.level_color[level] = colorer

    # -------------------------------------------------------------------------
    def format(self, record):
        """
        Format the specified record as text.
        """

        record = copy.copy(record)
        levelname = record.levelname

        if levelname in self.level_color and self.level_color[levelname]:

            record.name = self.bold.coloring(record.name)
            record.filename = self.bold.coloring(record.filename)
            record.module = self.bold.coloring(record.module)
            record.funcName = self.bold.coloring(record.funcName)
            record.pathname = self.bold.coloring(record.pathname)
            record.processName = self.bold.coloring(record.processName)
            record.threadName = self.bold.coloring(record.threadName)

            colorer = self.level_color[levelname]
            record.levelname = colorer.coloring(levelname)
            record.msg = colorer.coloring(record.msg)

        return logging.Formatter.format(self, record)


# =============================================================================

if __name__ == "__main__":
    pass

# =============================================================================

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
