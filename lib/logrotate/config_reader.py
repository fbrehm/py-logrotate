#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: © 2010 - 2016 by Frank Brehm, Berlin
@summary: module the configuration parsing object for Python logrotating
"""

# Standard modules
import re
import sys
import gettext
import pprint
import os
import os.path
import pwd
import grp
import glob
import logging
import email.utils

# Third party modules
import six

from six.moves import shlex_quote

# Own modules
from logrotate.common import split_parts, pp, email_valid, period2days
from logrotate.common import human2bytes, get_address_list
from logrotate.common import logrotate_gettext, logrotate_ngettext
from logrotate.common import to_str_or_bust as to_str

from logrotate.base import BaseObjectError, BaseObject

from logrotate.script import LogRotateScript

__version__    = '0.2.2'

_ = logrotate_gettext
__ = logrotate_ngettext

LOG = logging.getLogger(__name__)


#========================================================================
# Module variables

# @var: dict with all valid taboo pattern types as keys
#       and the resulting regex template for the filename as value
pattern_types = {
    'ext':    r'%s$',
    'file':   r'^%s$',
    'prefix': r'^%s',
}

script_directives = [
    'postrotate',
    'prerotate',
    'firstaction',
    'lastaction',
]

unsupported_options = (
    'uncompresscmd',
    'error',
)

options_with_values = (
    'mail',
    'compresscmd',
    'statusfile',
    'pidfile',
    'compressext',
    'rotate',
    'maxage',
    'mailfrom',
    'smtphost',
    'smtpport',
    'smtptls',
    'smtpuser',
    'smtppasswd',
)

boolean_options = (
    'compress',
    'copy',
    'copytruncate',
    'ifempty',
    'missingok',
    'sharedscripts',
)

integer_options = (
    'delaycompress',
    'rotate',
    'start',
)

string_options = (
    'extension',
    'compresscmd',
    'compressext',
    'compressoptions',
)

global_options = (
    'statusfile',
    'pidfile',
    'mailfrom',
    'smtphost',
    'smtpport',
    'smtptls',
    'smtpuser',
    'smtppasswd',
)

path_options = (
    'statusfile',
    'pidfile',
)

valid_periods = {
    'hourly':   (1/24),
    '2hourly':  (1/12),
    '4hourly':  (1/6),
    '6hourly':  (1/4),
    '12hourly': (1/2),
    'daily':    1,
    '2daily':   2,
    'weekly':   7,
    'monthly':  30,
    '2monthly': 60,
    '4monthly': 120,
    '6monthly': 182,
    'yearly':   365,
}

yes_values = (
    '1',
    'on',
    'y',
    'yes',
    'true',
)

no_values = (
    '0',
    'off',
    'n',
    'no',
    'false',
)

#========================================================================

class LogrotateConfigurationError(Exception):
    '''
    Base class for exceptions in this module.
    '''
    pass

#========================================================================

class LogrotateConfigurationReader(object):
    '''Class for reading the configuration for Python logrotating'''

    #-------------------------------------------------------
    def __init__( self, config_file,
                        verbose   = 0,
                        local_dir = None,
                        test_mode = False,
    ):
        '''
        Constructor.

        @param config_file: the configuration file to use
        @type config_file:  str
        @param verbose:     verbosity (debug) level
        @type verbose:      int
        @param local_dir:   The directory, where the i18n-files (*.mo)
                            are located. If None, then system default
                            (/usr/share/locale) is used.
        @type local_dir:    str or None
        @param test_mode:   test mode - no write actions are made
        @type test_mode:    bool

        @return: None
        '''

        self.local_dir = local_dir
        '''
        @ivar: The directory, where the i18n-files (*.mo) are located.
        @type: str or None
        '''

        self.verbose = verbose
        '''
        @ivar: verbosity level (0 - 9)
        @type: int
        '''

        self.config_file = config_file
        '''
        @ivar: the initial configuration file to use
        @type: str
        '''

        self.test_mode = test_mode
        '''
        @ivar: test mode - no write actions are made
        @type: bool
        '''

        self.global_option = {}
        '''
        @ivar: all global options
        @type: dict
        '''
        self.global_option['smtphost'] = ''

        #############################################
        # the rest of instance variables:

        self.search_path = ['/bin', '/usr/bin']
        '''
        @ivar: ordered list with directories, where executables are searched
        @type: list
        '''
        self._init_search_path()

        self.shred_command = '/usr/bin/shred'
        '''
        @ivar: the system command to shred aged rotated logfiles, if wanted
        @type: str
        '''
        self.check_shred_command()

        self.default = {}
        '''
        @ivar: the default values for  directives
        @type: dict
        '''
        self._reset_defaults()

        self.new_log = None
        '''
        @ivar: struct with the current log definition
        @type: dict or None
        '''

        self.taboo = []
        '''
        @ivar: taboo patterns for including files of whole directories
        @type: list
        '''
        self.add_taboo(r'\.rpmnew',        'ext');
        self.add_taboo(r'\.rpmorig',       'ext');
        self.add_taboo(r'\.rpmsave',       'ext');
        self.add_taboo(r',v',              'ext');
        self.add_taboo(r'\.swp',           'ext');
        self.add_taboo(r'~',               'ext');
        self.add_taboo(r'\.',              'prefix');
        self.add_taboo(r'\.bak',           'ext');
        self.add_taboo(r'\.old',           'ext');
        self.add_taboo(r'\.rej',           'ext');
        self.add_taboo(r'CVS',             'file');
        self.add_taboo(r'RCS',             'file');
        self.add_taboo(r'\.disabled',      'ext');
        self.add_taboo(r'\.dpkg-old',      'ext');
        self.add_taboo(r'\.dpkg-dist',     'ext');
        self.add_taboo(r'\.dpkg-new',      'ext');
        self.add_taboo(r'\.cfsaved',       'ext');
        self.add_taboo(r'\.ucf-old',       'ext');
        self.add_taboo(r'\.ucf-dist',      'ext');
        self.add_taboo(r'\.ucf-new',       'ext');
        self.add_taboo(r'\.cfsaved',       'ext');
        self.add_taboo(r'\.rhn-cfg-tmp-*', 'ext');

        self.config_files = {}
        '''
        @ivar: dict with all called and included configuration files
               to avoid double including
        @type: dict
        '''

        self.config_was_read = False
        '''
        @ivar: flag whether the configuration file was read.
        @type: bool
        '''

        self.config = []
        '''
        @ivar: the configuration, how it was read from cofiguration file(s)
        @type: list
        '''

        self.scripts = {}
        '''
        @ivar: dict of LogRotateScript objects
               with all named scripts found in configuration
        @type: dict
        '''

        self.defined_logfiles = {}
        '''
        @ivar: all even defined logfiles after globing of file patterns
        @type: dict
        '''

        LOG.debug( _("Logrotate config reader initialised.") )

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        pp = pprint.PrettyPrinter(indent=4)
        structure = self.as_dict()
        return pp.pformat(structure)

    #-------------------------------------------------------
    def as_dict(self):
        '''
        Transforms the elements of the object into a dict

        @return: structure as dict
        @rtype:  dict
        '''

        res = {
            'config':           self.config,
            'config_file':      self.config_file,
            'config_files':     self.config_files,
            'config_was_read':  self.config_was_read,
            'default':          self.default,
            'defined_logfiles': self.defined_logfiles,
            'global_option':    self.global_option,
            'local_dir':        self.local_dir,
            'new_log':          self.new_log,
            'search_path':      self.search_path,
            'scripts':          {},
            'shred_command':    self.shred_command,
            'taboo':            self.taboo,
            'test_mode':        self.test_mode,
            'verbose':          self.verbose,
        }

        for script_name in self.scripts.keys():
            res['scripts'][script_name] = self.scripts[script_name].as_dict()

        return res

    #------------------------------------------------------------
    def _reset_defaults(self):
        '''
        Resetting self.default to the hard coded values
        '''

        if self.verbose > 3:
            msg = _("Resetting default values for directives " +
                    "to hard coded values.")
            LOG.debug(msg)

        self.default = {}

        self.default['compress']      = False
        self.default['compresscmd']   = 'internal_gzip'
        self.default['compressext']   = None
        self.default['compressoptions']  = None
        self.default['copy']          = False
        self.default['copytruncate']  = False
        self.default['create']        = {
            'enabled': False,
            'mode':    None,
            'owner':   None,
            'group':   None,
        }
        self.default['period']        = 7
        self.default['dateext']       = False
        self.default['datepattern']   = '%Y-%m-%d'
        self.default['delaycompress'] = None
        self.default['extension']     = ""
        self.default['ifempty']       = True
        self.default['mailaddress']   = None
        self.default['mailfirst']     = None
        self.default['maxage']        = None
        self.default['missingok']     = False
        self.default['olddir']        = {
            'dirname':    '',
            'dateformat': False,
            'enabled':    False,
            'mode':       None,
            'owner':      None,
            'group':      None,
        }
        self.default['rotate']        = 4
        self.default['sharedscripts'] = False
        self.default['shred']         = False
        self.default['size']          = None
        self.default['start']         = 0

    #------------------------------------------------------------
    def add_taboo(self, pattern, pattern_type = 'file'):
        '''
        Add a pattern to the list of taboo patterns self.taboo
        Raises a general exception, if pattern_type is invalid

        @param pattern:      The patten to append to the taboo list
        @type pattern:       str
        @param pattern_type: The type of the taboo pattern
                            ('ext', 'file' or 'prefix')
        @type pattern_type:  str

        @return: None
        '''

        if not pattern_type in pattern_types:
            msg = _("Invalid taboo pattern type '%s' given.") % (pattern_type)
            raise Exception(msg)

        pattern = ( pattern_types[pattern_type] % pattern )
        if self.verbose > 3:
            msg = _("New taboo pattern: '%s'.") % (pattern)
            LOG.debug(msg)

        self.taboo.append(pattern)

    #------------------------------------------------------------
    def _init_search_path(self):
        '''
        Initialises the internal list of search pathes

        @return: None
        '''

        dir_included = {}

        # Including default path list from environment $PATH
        def_path = os.environ['PATH']
        if not def_path:
            def_path = ''
        sep = os.pathsep
        path_list = []
        for item in def_path.split(sep):
            if item:
                if os.path.isdir(item):
                    real_dir = os.path.abspath(item)
                    if not real_dir in dir_included:
                        path_list.append(real_dir)
                        dir_included[real_dir] = True
                else:
                    msg = _("'%s' is not a directory.") % (item) 
                    LOG.debug(msg)
                        
        # Including default path list from python
        def_path = os.defpath
        for item in def_path.split(sep):
            if item:
                if os.path.isdir(item):
                    real_dir = os.path.abspath(item)
                    if not real_dir in dir_included:
                        path_list.append(real_dir)
                        dir_included[real_dir] = True
                else:
                    msg = _("'%s' is not a directory.") % (item) 
                    LOG.debug(msg)

        # Including own defined directories
        for item in ('/usr/local/bin',
                     '/sbin',
                     '/usr/sbin',
                     '/usr/local/sbin'):
            if os.path.isdir(item):
                real_dir = os.path.abspath(item)
                if not real_dir in dir_included:
                    path_list.append(real_dir)
                    dir_included[real_dir] = True
            else:
                msg = _("'%s' is not a directory.") % (item) 
                LOG.debug(msg)

        self.search_path = path_list

    #------------------------------------------------------------
    def _get_std_search_path(self, include_current = False):
        '''
        Returns a list with all search directories from $PATH
        and some additionally directiories.

        @param include_current: include the current working directory
                                at the end of the list
        @type include_current:  bool

        @return: list of search directories
        @rtype:  list
        '''

        path_list = self.search_path
        if include_current:
            item = os.getcwd()
            real_dir = os.path.abspath(item)
            path_list.append(real_dir)

        return path_list

    #------------------------------------------------------------
    def check_shred_command(self):
        '''
        Checks the availability of a check command. Sets self.shred_command to
        this system command or to None, if not found (including a warning).
        '''

        path_list = self._get_std_search_path(True)

        cmd = None
        found = False
        for search_dir in path_list:
            if os.path.isdir(search_dir):
                cmd = os.path.join(search_dir, 'shred')
                if not os.path.isfile(cmd):
                    continue
                if os.access(cmd, os.X_OK):
                    found = True
                    break
            else:
                msg = _("Search path '%s' doesn't exists or is not "
                         + "a directory.") \
                        % (search_dir)
                LOG.debug(msg)

        if found:
            msg = _("Shred command found: '%s'.") % (cmd)
            LOG.debug(msg)
            self.shred_command = cmd
            return True
        else:
            msg = _("Shred command not found, shred disabled.")
            LOG.warning(msg)
            self.shred_command = None
            return False

    #------------------------------------------------------------
    def check_compress_command(self, command):
        '''
        Checks the availability of the given compress command.

        'internal_zip, 'internal_gzip' and 'internal_bzip2' are accepted as
        valid compress commands for compressing
        with the appropriate python modules.

        @param command: command to validate (absolute or relative for
                        searching in standard search path)
        @type command:  str

        @return: absolute path of the compress command, 'internal_gzip',
                 'internal_bzip2' or None if not found or invalid
        @rtype:  str or None
        '''

        path_list = self._get_std_search_path(True)
 
        pat = r'^\s*internal[\-_\s]?zip\s*'
        match = re.search(pat, command, re.IGNORECASE)
        if match:
            return 'internal_zip'

        pat = r'^\s*internal[\-_\s]?gzip\s*'
        match = re.search(pat, command, re.IGNORECASE)
        if match:
            return 'internal_gzip'

        pat = r'^\s*internal[\-_\s]?bzip2\s*'
        match = re.search(pat, command, re.IGNORECASE)
        if match:
            return 'internal_bzip2'

        if os.path.isabs(command):
            if os.access(command, os.X_OK):
                return os.path.abspath(command)
            else:
                return None

        cmd = None
        found = False
        for search_dir in path_list:
            if os.path.isdir(search_dir):
                cmd = os.path.join(search_dir, command)
                if not os.path.isfile(cmd):
                    continue
                if os.access(cmd, os.X_OK):
                    found = True
                    break
            else:
                msg = _("Search path '%s' doesn't exists or "
                         + "is not a directory.") % (search_dir)
                LOG.debug(msg)

        if found:
            return os.path.abspath(cmd)
        else:
            return None

    #------------------------------------------------------------
    def get_config(self):
        '''
        Returns the configuration, how it was read from configuration file(s)

        @return: configuration
        @rtype:  dict or None
        '''

        if not self._read_main_configfile():
            return None

        return self.config

    #------------------------------------------------------------
    def get_scripts(self):
        '''
        Returns the scriptlist, how it was read from configuration file(s)

        @return: list of scripts
        @rtype:  list
        '''

        if not self._read_main_configfile():
            return None

        return self.scripts

    #------------------------------------------------------------
    def _read_main_configfile(self):
        '''
        Reads the main configuration file (self.config_file).

        @return: success of reading
        @rtype:  bool
        '''

        if self.config_was_read:
            return True

        if not os.path.exists(self.config_file):
            msg = _("File '%s' doesn't exists.") % (self.config_file)
            raise LogrotateConfigurationError(msg)

        self.config_file = os.path.abspath(self.config_file)

        if not self._read(self.config_file):
            return None

        self.config_was_read = True
        return True

    #------------------------------------------------------------
    def _read(self, configfile):
        '''
        Reads the configuration from given configuration file and all
        included files.

        @param configfile: the configfile to read
        @type configfile:  str
        '''

        pp = pprint.PrettyPrinter(indent=4)
        msg = _("Try reading configuration from '%s' ...") % (configfile)
        LOG.debug(msg)

        if not os.path.exists(configfile):
            msg = _("File '%s' doesn't exists.") % (configfile)
            raise LogrotateConfigurationError(msg)

        if not os.path.isfile(configfile):
            msg = _("'%s' is not a regular file.") % (configfile)
            raise LogrotateConfigurationError(msg)

        self.config_files[configfile] = True

        msg = _("Reading configuration from '%s' ...") % (configfile)
        LOG.info(msg)

        cfile = None
        try:
            cfile = open(configfile, 'Ur')
        except IOError, e:
            msg = _("Could not read configuration file '%s'") % (configfile)
            msg += ': ' + str(e)
            raise LogrotateConfigurationError(msg)
        lines = cfile.readlines()
        cfile.close()

        # defaults for the big loop
        linenr          = 0
        in_fd           = False
        in_script       = False
        in_logfile_list = False
        lastrow         = ''
        newscript       = ''

        # inspect every line of configuration file
        for line in lines:

            linenr += 1
            line = line.strip()

            # Perform a backslash at the end of the line
            line = lastrow + line
            match = re.search(r'\\$', line)
            if match:
                line = re.sub(r'\\$', '', line)
                lastrow = line
                continue
            lastrow = ''

            # delete comments
            line = re.sub(r'^#.*', '', line)
            if line == '':
                continue

            # perform script content
            if in_script:
                match = re.search(r'^endscript$', line)
                if match:
                    in_script = False
                    continue
                #self.scripts[newscript]['cmd'].append(line)
                self.scripts[newscript].add_cmd(line)
                continue

            # start of a logfile definition
            if line == '{':

                if self.verbose > 3:
                    msg = _("Starting a logfile definition.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.debug(msg)

                self._start_logfile_definition( 
                    line            = line,
                    filename        = configfile,
                    in_fd           = in_fd,
                    in_logfile_list = in_logfile_list,
                    linenr          = linenr
                )
                in_fd = True
                in_logfile_list = False
                continue

            # start of a logfile pattern
            match = re.search(r'^[\'"]', line)
            if match or os.path.isabs(line):

                if in_fd:
                    msg = _("Logfile pattern definition not allowed inside "
                             + "a logfile definition.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    raise LogrotateConfigurationError(msg)
                do_start_logfile_definition = False

                # look, whether a start of a logfile definition is necessary
                match_bracket = re.search(r'\s*{\s*$', line)
                if match_bracket:
                    line = re.sub(r'\s*{\s*$', '', line)
                    do_start_logfile_definition = True
                if not in_logfile_list:
                    self._start_new_log(configfile, linenr)
                in_logfile_list = True

                parts = split_parts(line)
                if self.verbose > 3:
                    msg =  _("Split into parts of: '%s'") % (line)
                    msg += ":\n" + pp.pformat(parts)
                    LOG.debug(msg)

                for pattern in parts:
                    if pattern == '{':
                        msg = _("Syntax error: open curly bracket inside a"
                                + "logfile pattern definition.")
                        msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                        % {'file': configfile, 'lnr': linenr})
                        raise LogrotateConfigurationError(msg)
                    self.new_log['file_patterns'].append(pattern)

                # start of a logfile definition, if necessary
                if do_start_logfile_definition:
                    self._start_logfile_definition( 
                        line            = line,
                        filename        = configfile,
                        in_fd           = in_fd,
                        in_logfile_list = in_logfile_list,
                        linenr          = linenr
                    )
                    in_fd = True
                    in_logfile_list = False

                continue

            # end of a logfile definition
            match = re.search(r'^}(.*)', line)
            if match:
                if not in_fd:
                    msg = _("Syntax error: unbalanced closing curly " +
                            "bracket found.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    raise LogrotateConfigurationError(msg)
                rest = match.group(1)
                if self.verbose > 2:
                    msg = _("End of a logfile definition.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.debug(msg)
                if rest:
                    msg = (_("Needless content found at the end of a logfile "
                             "definition found: '%s'.") % (str(rest)))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.warning(msg)
                # set a compress ext, if Compress is True
                if self.new_log['compress']:
                    if not self.new_log['compressext']:
                        if self.new_log['compresscmd'] == 'internal_gzip':
                            self.new_log['compressext'] = '.gz'
                        elif self.new_log['compresscmd'] == 'internal_zip':
                            self.new_log['compressext'] = '.zip'
                        elif self.new_log['compresscmd'] == 'internal_bzip2':
                            self.new_log['compressext'] = '.bz2'
                        else:
                            msg = (_("No extension for compressed logfiles " +
                                     "given (File of definition: '%(file)s'," +
                                     " start definition: %(rownum)d).")
                                  % {'file': self.new_log['configfile'],
                                     'rownum': self.new_log['configrow']})
                            raise LogrotateConfigurationError(msg)
                # set ifempty => True, if a minsize was given
                if self.new_log['size']:
                    self.new_log['ifempty'] = False
                found_files = self._assign_logfiles()
                if self.verbose > 3:
                    msg =  _("New logfile definition:")
                    msg += "\n" + pp.pformat(self.new_log)
                    LOG.debug(msg)
                if found_files > 0:
                    if self.new_log['postrotate']:
                        script = self.new_log['postrotate']
                        if self.scripts[script]:
                            self.scripts[script].post_files += found_files
                        else:
                            msg = (_("Postrotate script '%s' not found.")
                                    % (script))
                            LOG.error(msg)
                    if self.new_log['lastaction']:
                        script = self.new_log['lastaction']
                        if self.scripts[script]:
                            self.scripts[script].last_files += found_files
                        else:
                            msg = (_("Lastaction script '%s' not found.")
                                    % (script))
                            LOG.error(msg)
                    self.config.append(self.new_log)
                in_fd = False
                in_logfile_list = False

                continue

            # performing includes
            match = re.search(r'^include(?:\s+(.*))?$', line, re.IGNORECASE)
            if match:
                rest = match.group(1)
                if in_fd or in_logfile_list:
                    msg = _("Syntax error: include may not appear inside of "
                             + "log file definition.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.warning(msg)
                    continue
                self._do_include(line, rest, configfile, linenr)
                continue

            # start of a (regular) script definition
            pattern = r'^(' + '|'.join(script_directives) + r')(\s+.*)?$'
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                script_type = match.group(1).lower()
                script_name = None
                if match.group(2) is not None:
                    values      = split_parts(match.group(2))
                    if values[0]:
                        script_name = values[0]
                if self.verbose > 3:
                    msg = _("Found start of a regular script definition: " 
                             + "type: '%(type)s', name: '%(name)s'.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.debug(msg)
                newscript = self._start_log_script_definition(
                    script_type = script_type,
                    script_name = script_name,
                    line        = line,
                    filename    = configfile,
                    in_fd       = in_fd,
                    linenr      = linenr,
                )
                if newscript:
                    in_script = True
                if self.verbose > 3:
                    msg = _("New log script name: '%s'.") % (newscript)
                    LOG.debug(msg)
                continue

            # start of an explicite external script definition
            match = re.search(r'^script(\s+.*)?$', line, re.IGNORECASE)
            if match:
                if self.verbose > 3:
                    msg = _("Found start of a external script definition.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.debug(msg)
                rest = match.group(1)
                if in_fd or in_logfile_list:
                    msg = _("Syntax error: external script definition may "
                             + "not appear inside of a log file definition.")
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': configfile, 'lnr': linenr})
                    LOG.warning(msg)
                    continue
                newscript = self._ext_script_definition(
                    line, rest, configfile, linenr
                )
                if newscript:
                    in_script = True
                if self.verbose > 3:
                    msg = _("New external script name: '%s'.") % (newscript)
                    LOG.debug(msg)
                continue

            # all other options
            if not self._option(line, in_fd, configfile, linenr):
                msg = _("Syntax error in file '%(file)s', line %(line)s") \
                        % {'file': configfile, 'line': linenr}
                LOG.warning(msg)

        return True

    #------------------------------------------------------------
    def _option(self, line, in_fd, filename, linenr):
        '''
        Checks the given line as a logrotate option and assign this
        option on success to the default options or in the current
        logfile directive

        @param line:     line of current config file
        @type line:      str
        @param in_fd:    parsing inside a logfile definition
        @type in_fd:     bool
        @param filename: current configuration file
        @type filename:  str
        @param linenr:   current line number of configuration file
        @type linenr:    int

        @return: success of parsing this option
        @rtype:  bool
        '''

        if self.verbose > 4:
            msg = _("Checking line '%s' for a logrotate option.") % (line)
            msg += " " + (_("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.debug(msg)

        # where to insert the option?
        directive = self.default
        directive_str = 'default'
        if in_fd:
            directive = self.new_log
            directive_str = 'new_log'

        # extract option from line
        option = None
        val    = None
        match = re.search(r'^(\S+)\s*(.*)', line)
        if match:
            option = match.group(1).lower()
            val    = match.group(2)
        else:
            msg = _("Could not detect option in line '%s'.") % (line)
            LOG.warning(msg)
            return False
        val = re.sub(r'^\s+$', '', val)
        if self.verbose > 4:
            msg = (_("Found option '%(opt)s' with value '%(val)s'.")
                    % {'opt': option, 'val': val})
            LOG.debug(msg)

        # Check for unsupported options
        pattern = r'^(' + '|'.join(unsupported_options) + r')$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            msg = _("Unsupported option '%s'.") % (match.group(1).lower())
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.info(msg)
            return True

        # Check for boolean option
        pattern = r'^(not?)?(' + '|'.join(boolean_options) + r')$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            negated = match.group(1)
            key     = match.group(2).lower()
            if val:
                msg = (_("Found value '%(value)s' behind the boolean option " +
                         "'%(option)s', ignoring.")
                        % {'value': val, 'option': option})
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.warning(msg)
            if negated is None:
                option_value = True
            else:
                option_value = False
            if self.verbose > 4:
                msg = (_("Setting boolean option '%(option)s' in " +
                         "'%(directive)s' to '%(value)s'.")
                         % {'option': key,
                            'directive': directive_str,
                            'value': str(option_value)
                           })
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            directive[key] = option_value
            if key == 'copy' and option_value:
                if directive['copytruncate']:
                    msg = (_("Option '%(by)s' disables option '%(what)s'.")
                            % {'by': 'copy', 'what': 'copytruncate'})
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.warning(msg)
                    directive['copytruncate'] = False
                if directive['create']['enabled']:
                    msg = (_("Option '%(by)s' disables option '%(what)s'.")
                            % {'by': 'copy', 'what': 'create'})
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.warning(msg)
                    directive['create']['enabled'] = False
            elif key == 'copytruncate' and option_value:
                if directive['copy']:
                    msg = (_("Option '%(by)s' disables option '%(what)s'.")
                            % {'by': 'copytruncate', 'what': 'copy'})
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.warning(msg)
                    directive['copy'] = False
                if directive['create']['enabled']:
                    msg = (_("Option '%(by)s' disables option '%(what)s'.")
                            % {'by': 'copytruncate', 'what': 'create'})
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.warning(msg)
                    directive['create']['enabled'] = False
            return True

        # Check for integer options
        pattern = r'^(not?)?(' + '|'.join(integer_options) + r')$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            negated = match.group(1)
            key     = match.group(2).lower()
            option_value = 0
            if negated is None:
                if key in options_with_values:
                    if val is None or val == '':
                        msg = _("Option '%s' must have a value.") % (key)
                        LOG.warning(msg)
                        return False
                else:
                    if val is None or val == '':
                        val = '1'
                try:
                    option_value = long(val)
                except ValueError, e:
                    msg = _("Option '%(option)s' has no "
                             + "integer value: %(msg)s.") \
                            % {'option': key, 'msg': str(e)}
                    LOG.warning(msg)
                    return False
            if option_value < 0:
                msg = _("Negative value %(value)s for option '%(option)s' "
                         + "is not allowed.") \
                            % {'value': str(option_value), 'option': key}
                LOG.warning(msg)
                return False
            if self.verbose > 4:
                msg = (_("Setting integer option '%(option)s' " +
                         "in '%(directive)s' to '%(value)s'.")
                        % { 'option': key,
                            'directive': directive_str,
                            'value': str(option_value)
                          })
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            directive[key] = option_value
            return True

        # Check for mail address
        match = re.search(r'^(not?)?mail$', option, re.IGNORECASE)
        if match:
            negated = match.group(1)
            if negated:
                directive['mailaddress'] = None
                if val is not None and val != '':
                    msg = (_("Senseless option value '%(value)s' " +
                             "after '%(option)s'.")
                            % {'value': val, 'option': option.lower()})
                    LOG.warning(msg)
                    return False
                return True
            address_list = get_address_list(val, self.verbose)
            if len(address_list):
                directive['mailaddress'] = address_list
            else:
                directive['mailaddress'] = None
            if self.verbose > 4:
                pp = pprint.PrettyPrinter(indent=4)
                msg = _("Setting mail address in '%(directive)s' to "
                         + "'%(addr)s'.") \
                    % {
                        'directive': directive_str,
                        'addr': pp.pformat(directive['mailaddress']),
                      }
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            return True

        # Check for mailfirst/maillast
        match = re.search(r'^mail(first|last)$', option, re.IGNORECASE)
        if match:
            when = match.group(1).lower()
            option_value = False
            if when == 'first':
                option_value = True
            directive['mailfirst'] = option_value
            if self.verbose > 4:
                msg = _("Setting mailfirst in '%(directive)s' "
                         + "to '%(value)s'.") \
                        % { 'directive': directive_str,
                            'value': str(option_value)
                          }
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            if val is not None and val != '':
                msg = _("Senseless option value '%(value)s' after "
                         + "'%(option)s'.") \
                        % {'value': val, 'option': option.lower()}
                LOG.warning(msg)
                return False
            return True

        # Check for string options
        pattern = r'^(' + '|'.join(string_options) + r')$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            key = match.group(1).lower()
            if key in options_with_values:
                if self.verbose > 5:
                    msg = _("Option '%s' must have a value.") % (key)
                    LOG.debug(msg)
                if (val is None) or (val == ''):
                    msg = _("Option '%s' without a value.") % (key)
                    LOG.debug(msg)
                    return False
            if key == 'compresscmd':
                prog = self.check_compress_command(val)
                if prog is None:
                    msg =  _("Compress command '%s' not found.") % (val)
                    LOG.warning(msg)
                    return False
                val = prog
            if key == 'compressoptions' and val is None:
                val = ''
            directive[key] = val
            return True

        # Check for global options
        pattern = r'^(' + '|'.join(global_options) + r')$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            key = match.group(1).lower()
            if in_fd:
                msg = (_("Option '%s' not allowed inside a logfile directive.")
                        %(key))
                LOG.warning(msg)
                return False
            if key in options_with_values:
                if self.verbose > 5:
                    msg = (_("Option '%s' must have a value.") % (key))
                    LOG.debug(msg)
                if (val is None) or (re.search(r'^\s*$', val) is not None):
                    msg = _("Option '%s' without a value.") % (key)
                    LOG.warning(msg)
                    return False
            if key in path_options:
                if not os.path.abspath(val):
                    msg = (_("Value '%(value)s' for option '%(option)s' " +
                             "is not an absolute path.")
                            % {'value': val, 'option': key})
                    LOG.warning(msg)
                    return False
            if key == 'mailfrom':
               pair = email.utils.parseaddr(val)
               if not email_valid(pair[1]):
                    msg = (_("Invalid mail address for 'mailfrom' " +
                             "given: '%s'.") % (val))
                    LOG.warning(msg)
                    return False
               val = pair
            elif key == 'smtpport':
                port = 25
                try:
                    port = int(val)
                except ValueError, e:
                    msg = _("Invalid SMTP port '%s' given.") % (val)
                    LOG.warning(msg)
                    return False
                if port < 1 or port >= 2**15:
                    msg = _("Invalid SMTP port '%s' given.") % (val)
                    LOG.warning(msg)
                    return False
                val = port
            elif key == 'smtptls':
                use_tls = False
                pat = r'^\s*(?:0+|false|no?)\s*$'
                match = re.search(pat, val, re.IGNORECASE)
                if not match:
                    pat = r'^\s*(?:1|true|y(?:es)?)\s*$'
                    match = re.search(pat, val, re.IGNORECASE)
                    if match:
                        use_tls = True
                    else:
                        use_tls = bool(val)
                val = use_tls
            if self.verbose > 4:
                msg = (_("Setting global option '%(option)s' " +
                         "to '%(value)s'.")
                        % {'option': key, 'value': val})
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            self.global_option[key] = val
            return True

        # Check for rotation period
        pattern = r'^(' + '|'.join(valid_periods.keys()) + r'|period)$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            key = match.group(1).lower()
            if self.verbose > 4:
                msg = (_("Checking for option 'period': key '%(key)s', " +
                         "value '%(value)s'.")
                        % {'key': key, 'value': val})
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            option_value = 1
            if key in valid_periods:
                if (val is not None) and (re.search(r'^\s*$', val) is None):
                    msg = (_("Option '%(option)s' may not have a " +
                             "value ('%(value)s').")
                            % {'option': key, 'value': val})
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                        % {'file': filename, 'lnr': linenr})
                    LOG.warning(msg)
                option_value = valid_periods[key]
            else:
                try:
                    option_value = period2days(val, verbose = self.verbose)
                except ValueError, e:
                    msg = _("Invalid period definition: '%s'.") % (val)
                    LOG.warning(msg)
                    return False
            if self.verbose > 4:
                msg = (_("Setting '%(what)s' in '%(directive)s' " +
                         "to %(to)f days.")
                        % { 'what': 'period',
                            'directive': directive_str,
                            'to': option_value,
                          })
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            directive['period'] = option_value
            return True

        # get maximum age of old rotated log files
        match = re.search(r'^(not?)?maxage$', option, re.IGNORECASE)
        if match:
            negated = False
            if match.group(1) is not None:
                negated = True
            if (val is None) or re.search(r'^\s*$', val) is not None:
                negated = True
            option_value = 0
            if not negated:
                try:
                    option_value = period2days(val, verbose = self.verbose)
                except ValueError, e:
                    msg = _("Invalid maxage definition: '%s'") % (val)
                    LOG.warning(msg)
                    return False
            if self.verbose > 4:
                msg = (_("Setting '%(what)s' in '%(directive)s' " +
                         "to %(to)f days.")
                        % { 'what': 'maxage',
                            'directive': directive_str,
                            'to': option_value,
                          })
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            directive['maxage'] = option_value
            return True

        # Setting date extension of rotated log files
        match = re.search(r'^(no)?dateext$', option, re.IGNORECASE)
        if match:

            negated = False
            if match.group(1) is not None:
                negated = True
            use_dateext = False
            dateext = None

            if self.verbose > 4:
                msg = (_("Checking for option 'dateext', negated: '%s'.")
                        % (str(negated)))
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            values = []
            if val is not None:
                values = split_parts(val) 

            if not negated:
                first_val = ''
                if len(values) > 0:
                    first_val = values[0].lower()
                option_value = first_val
                if first_val is None or \
                        re.search(r'^\s*$', first_val) is not None:
                    option_value = 'true'
                if self.verbose > 5:
                    msg = (_("'dateext': first_val: '%(first_val)s', " +
                             "option_value: '%(value)s'.")
                            % {'first_val': first_val, 'value': option_value})
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                if option_value in yes_values:
                    use_dateext = True
                elif option_value in no_values:
                    use_dateext = False
                else:
                    use_dateext = True
                    dateext = val

            if self.verbose > 4:
                msg = (_("Setting '%(what)s' in '%(directive)s' to %(to)s.")
                        % { 'what': 'dateeext',
                            'directive': directive_str,
                            'to': str(use_dateext)
                          })
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            directive['dateext'] = use_dateext

            if dateext is not None:
                if self.verbose > 4:
                    msg = (_("Setting '%(what)s' in '%(directive)s' " +
                             "to %(to)s.")
                            % { 'what': 'datepattern',
                                'directive': directive_str,
                                'to': dateext
                            })
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                directive['datepattern'] = dateext

            return True

        # Checking for create options ...
        match = re.search(r'(not?)?create$', option, re.IGNORECASE)
        if match:

            negated = False
            if match.group(1) is not None:
                negated = True

            if self.verbose > 5:
                msg = _("Checking for option '%s' ...") % ('create')
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)

            if negated:
                if self.verbose > 4:
                    msg = _("Removing '%s'.") % ('create')
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                directive['create']['enabled'] = False
                return True

            if directive['copy']:
                msg = _("Option '%s' was set, so option 'create' "
                         + "has no effect.") % ('copy')
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.warning(msg)
                directive['create']['enabled'] = False
                return True

            if directive['copytruncate']:
                msg = _("Option '%s' was set, so option 'create' "
                         + "has no effect.") % ('copytruncate')
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.warning(msg)
                directive['create']['enabled'] = False
                return True

            values = []
            if val is not None:
                values = split_parts(val)

            directive['create']['enabled'] = True

            mode  = None
            owner = None
            group = None

            # Check for create mode
            if len(values) > 0:
                if self.verbose > 5:
                    msg = (_("Trying to determine create mode '%s' ...")
                            % ('values[0]'))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                mode_octal = values[0]
                if re.search(r'^0', mode_octal) is None:
                    mode_octal = '0' + mode_octal
                try:
                    mode = int(mode_octal, 8)
                except ValueError:
                    msg = _("Invalid create mode '%s'.") % (values[1])
                    LOG.warning(msg)
                    return False

            # Check for Owner (user, uid)
            if len(values) > 1:
                owner_raw = values[1]
                if self.verbose > 5:
                    msg = (_("Trying to determine create owner '%s' ...")
                            % (owner_raw))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                if re.search(r'^[1-9]\d*$', owner_raw) is not None:
                    owner = int(owner_raw)
                else:
                    try:
                        owner = pwd.getpwnam(owner_raw)[2]
                    except KeyError:
                        msg = (_("Invalid owner '%(owner)s' in '%(what)s'.")
                                % {'owner': owner_raw, 'what': 'create'})
                        LOG.warning(msg)
                        return False

            # Check for Group (gid)
            if len(values) > 2:
                group_raw = values[2]
                if self.verbose > 5:
                    msg = (_("Trying to determine create group '%s' ...")
                            % (group_raw))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                if re.search(r'^[1-9]\d*$', group_raw) is not None:
                    group = int(group_raw)
                else:
                    try:
                        group = grp.getgrnam(group_raw)[2]
                    except KeyError:
                        msg = (_("Invalid group '%(group)s' in '%(what)s'.")
                                    % {'group': group_raw, 'what': 'create'})
                        LOG.warning(msg)
                        return False

            # Give values back ...
            directive['create']['mode']  = mode
            directive['create']['owner'] = owner
            directive['create']['group'] = group
            return True

        # checking for olddir ...
        match = re.search(r'^(not?)?olddir$', option, re.IGNORECASE)
        if match:

            negated = False
            if match.group(1) is not None:
                negated = True

            if self.verbose > 5:
                msg = _("Checking for option '%s' ...") % ('olddir')
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)

            if negated:
                if self.verbose > 4:
                    msg = _("Removing '%s'.") % ('olddir')
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                directive['olddir']['enabled'] = False
                return True

            values = []
            if val is not None:
                values = split_parts(val)

            # Check for dirname of olddir
            if ((len(values) < 1) or
                    (values[0] is None) or
                    (re.search(r'^\s*$', values[0]) is not None)):
                msg = _("Option '%s' without a value given.") % ('olddir')
                LOG.warning(msg)
                return False
            directive['olddir']['dirname'] = values[0]
            directive['olddir']['enabled'] = True

            mode  = None
            owner = None
            group = None

            # Check for create mode of olddir
            if len(values) > 1:
                if self.verbose > 5:
                    msg = (_("Trying to determine olddir create " +
                             "mode '%s' ...") % (values[1]))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                mode_octal = values[1]
                if re.search(r'^0', mode_octal) is None:
                    mode_octal = '0' + mode_octal
                try:
                    mode = int(mode_octal, 8)
                except ValueError:
                    msg = (_("Invalid create mode '%s' in 'olddir'.")
                            % (values[1]))
                    LOG.debug(msg)
                    return False

            # Check for Owner (user, uid)
            if len(values) > 2:
                owner_raw = values[2]
                if self.verbose > 5:
                    msg = (_("Trying to determine olddir owner '%s' ...")
                                % (owner_raw))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                if re.search(r'^[1-9]\d*$', owner_raw) is not None:
                    owner = int(owner_raw)
                else:
                    try:
                        owner = pwd.getpwnam(owner_raw)[2]
                    except KeyError:
                        msg = (_("Invalid owner '%(owner)s' in '%(what)s'.")
                                    % {'owner': owner_raw, 'what': 'olddir'})
                        LOG.warning(msg)
                        return False

            # Check for Group (gid)
            if len(values) > 3:
                group_raw = values[3]
                if self.verbose > 5:
                    msg = (_("Trying to determine olddir group '%s' ...")
                            % (group_raw))
                    msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                    % {'file': filename, 'lnr': linenr})
                    LOG.debug(msg)
                if re.search(r'^[1-9]\d*$', group_raw) is not None:
                    group = int(group_raw)
                else:
                    try:
                        group = grp.getgrnam(group_raw)[2]
                    except KeyError:
                        msg = (_("Invalid group '%(group)s' in '%(what)s'.")
                                    % {'group': group_raw, 'what': 'olddir'})
                        LOG.warning(msg)
                        return False

            # Give values back ...
            directive['olddir']['mode']  = mode
            directive['olddir']['owner'] = owner
            directive['olddir']['group'] = group
            return True

        # Check for minimum size for ratation
        match = re.search(r'^size(?:(?:\s*=|\s)|$)', line, re.IGNORECASE)
        if match:
            size_str = re.sub(r'^size(?:\s*=\s*|\s+)', '', line)
            if self.verbose > 5:
                msg = (_("Checking for option 'size', value '%s' ...")
                        % (size_str))
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            if size_str is None:
                msg = _("Failing size definition.")
                LOG.warning(msg)
                return False
            size_bytes = None
            try:
                size_bytes = human2bytes(size_str, verbose = self.verbose)
            except ValueError, e:
                msg = _("Invalid definition for 'size': '%s'.") % (size_str)
                LOG.warning(msg)
                return False
            if self.verbose > 4:
                msg = (_("Got a rotation size in '%(directive)s' " +
                         "of %(bytes)d bytes.")
                        % {'directive': directive_str, 'bytes': size_bytes})
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)
            directive['size'] = size_bytes
            return True

        # Check for taboo options
        pattern = r'^taboo(ext|file|prefix)$'
        match = re.search(pattern, option, re.IGNORECASE)
        if match:
            key = match.group(1).lower()
            if self.verbose > 5:
                msg = (_("Checking for option 'taboo%(type)s', " +
                         "value: '%(value)s' ...")
                        % {'type': key, 'value': val})
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.debug(msg)

            if in_fd:
                msg = (_("Option 'taboo%s' not allowed inside " +
                         "a logfile directive.") % (key))
                LOG.warning(msg)
                return False

            values = []
            if val is not None:
                values = split_parts(val)

            extend = False
            if len(values) > 0 and values[0] is not None and values[0] == '+':
                extend = True
                values.pop(0)

            if len(values) < 1:
                msg = _("Option 'taboo%s' needs a value.") % (key)
                LOG.warning(msg)
                return False

            if not extend:
                self.taboo = []
            for extension in values:
                self.add_taboo(extension, key)

            return True

        # Option not found, I'm angry
        msg = _("Unknown option '%s'.") % (option)
        LOG.warning(msg)
        return False

    #------------------------------------------------------------
    def _ext_script_definition(self, line, rest, filename, linenr):
        '''
        Starts a new explicite external script definition.
        It raises a LogrotateConfigurationError on error.

        @param line:     line of current config file
        @type line:      str
        @param rest:     rest of the current line after »script«
        @type rest:      str
        @param filename: current configuration file
        @type filename:  str
        @param linenr:   current line number of configuration file
        @type linenr:    int

        @return: name of the script (if a new script definition) or None
        @rtype:  str or None
        '''

        # split the rest in chunks
        values = split_parts(rest)

        # insufficient arguments to include ...
        if len(values) < 1:
            msg = _("No script name given in a script directive.")
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)
            return None

        # to much arguments to include ...
        if len(values) > 1:
            msg = _("Only one script name is allowed in a script directive, "
                     + "the first one is used.")
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)

        script_name = values[0]

        if script_name in self.scripts:
            msg = _("Script name '%s' is allready declared, it will "
                     + "be overwritten.") % (script_name)
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)

        self.scripts[script_name] = LogRotateScript(
            name      = script_name,
            local_dir = self.local_dir,
            verbose   = self.verbose,
            test_mode = self.test_mode,
        )

        return script_name

    #------------------------------------------------------------
    def _do_include( self, line, rest, filename, linenr):
        '''
        Starts a new logfile definition.
        It raises a LogrotateConfigurationError on error.

        @param line:     line of current config file
        @type line:      str
        @param rest:     rest of the current line after »include«
        @type rest:      str
        @param filename: current configuration file
        @type filename:  str
        @param linenr:   current line number of configuration file
        @type linenr:    int

        @return: Success of include
        @rtype:  bool
        '''

        # split the rest in chunks
        values = split_parts(rest)

        # insufficient arguments to include ...
        if len(values) < 1:
            msg = _("No file or directory given in a include directive.")
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)
            return False

        # to much arguments to include ...
        if len(values) > 1:
            msg = _("Only one declaration of a file or directory is allowed "
                     + "in a include directive, the first one is used.")
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)

        include = values[0]

        # including object doesn't exists
        if not os.path.exists(include):
            msg = _("Including object '%s' doesn't exists.") % (include)
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)
            return False

        include = os.path.abspath(include)

        # including object is neither a regular file nor a directory
        if not (os.path.isfile(include) or os.path.isdir(include)):
            msg = _("Including object '%s' is neither a regular "
                     + "file  nor a directory.") % (include)
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            LOG.warning(msg)
            return False

        if self.verbose > 1:
            msg = _("Trying to include object '%s' ...") % (include)
            LOG.debug(msg)

        # including object is a regular file
        if os.path.isfile(include):
            if include in self.config_files:
                msg = _("Recursive including of '%s'.") % (include)
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.warning(msg)
                return False
            return self._read(include)

        # This should never happen ...
        if not os.path.isdir(include):
            msg = _("What the hell is this: '%s'.") % (include)
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            raise Exception(msg)

        # including object is a directory - include all files
        if self.verbose > 1:
            msg = _("Including directory '%s' ...") % (include)
            LOG.debug(msg)

        dir_list = os.listdir(include)
        for item in sorted(dir_list, key=str.lower):

            item_path = os.path.abspath(os.path.join(include, item))
            if self.verbose > 2:
                msg = (_("Including item '%(item)s' ('%(path)s') ...")
                        % {'item': item, 'path': item_path})
                LOG.debug(msg)

            # Skip directories
            if os.path.isdir(item_path):
                if self.verbose > 1:
                    msg = (_("Skip subdirectory '%s' in including.")
                            % (item_path))
                    LOG.debug(msg)
                continue

            # Skip non regular files
            if not os.path.isfile(item_path):
                msg = _("Item '%s' is not a regular file.") % (item_path)
                LOG.debug(msg)
                continue

            # Check for taboo pattern
            taboo_found = False
            for pattern in self.taboo:
                match = re.search(pattern, item)
                if match:
                    if self.verbose > 1:
                        msg = (_("Item '%(item)s' is matching pattern " +
                                 "'%(pattern)s', skiping.")
                                % {'item': item, 'pattern': pattern})
                        LOG.debug(msg)
                    taboo_found = True
                    break
            if taboo_found:
                continue

            # Check, whther it was former included
            if item_path in self.config_files:
                msg = _("Recursive including of '%s'.") % (item_path)
                msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                                % {'file': filename, 'lnr': linenr})
                LOG.warning(msg)
                return False
            self._read(item_path)

    #------------------------------------------------------------
    def _start_logfile_definition(
        self, line, filename, in_fd, in_logfile_list, linenr
    ):
        '''
        Starts a new logfile definition.
        It raises a LogrotateConfigurationError on error.

        @param line:            line of current config file
        @type line:             str
        @param filename:        current configuration file
        @type filename:         str
        @param in_fd:           parsing inside a logfile definition
        @type in_fd:            bool
        @param in_logfile_list: logfile pattern list was started
        @type in_logfile_list:  bool
        @param linenr:          current line number of configuration file
        @type linenr:           int

        @return: name of the script (if a new script definition) or None
        @rtype:  str or None
        '''

        if in_fd:
            msg = _("Nested logfile definitions are not allowed.")
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            raise LogrotateConfigurationError(msg)

        if not in_logfile_list:
            msg = _("No logfile pattern defined on starting a "
                     + "logfile definition.")
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            raise LogrotateConfigurationError(msg)

    #------------------------------------------------------------
    def _start_log_script_definition( self,
                                      script_type,
                                      script_name,
                                      line,
                                      filename,
                                      in_fd,
                                      linenr):
        '''
        Starts a new logfile definition or logfile refrence
        inside a logfile definition.
        It raises a LogrotateConfigurationError outside a logfile definition.

        @param script_type: postrotate, prerotate, firstaction
                            or lastaction
        @type script_type:  str
        @param script_name: name of refernced script
        @type script_name:  str or None
        @param line:        line of current config file
        @type line:         str
        @param filename:    current configuration file
        @type filename:     str
        @param in_fd:       parsing inside a logfile definition
        @type in_fd:        bool
        @param linenr:      current line number of configuration file
        @type linenr:       int

        @return: name of the script (if a new script definition) or None
        @rtype:  str or None
        '''

        if not in_fd:
            msg = _("Directive '%s' is not allowed outside of a " +
                    "logfile definition.") % (script_type)
            msg += " " + ( _("(file '%(file)s', line %(lnr)s)")
                            % {'file': filename, 'lnr': linenr})
            raise LogrotateConfigurationError(msg)

        if script_name:
            self.new_log[script_type] = script_name
            return None

        new_script_name = self._new_scriptname(script_type)

        self.scripts[new_script_name] = LogRotateScript(
            name      = new_script_name,
            local_dir = self.local_dir,
            verbose   = self.verbose,
            test_mode = self.test_mode,
        )

        self.new_log[script_type] = new_script_name

        return new_script_name

    #------------------------------------------------------------
    def _new_scriptname(self, script_type = 'script'):
        '''
        Retrieves a new, unique script name.

        @param script_type: prefix of the script name
        @type script_type:  str

        @return: a new, unique script name
        @rtype:  str
        '''

        i = 0
        template = script_type + "_%02d"
        name = template % (i)

        while True:

            if name in self.scripts:
                cmd = self.scripts[name].cmd
                if cmd is not None:
                    if len(cmd):
                        i += 1
                        name = template % (i)
                    else:
                        break
                else:
                    break
            else:
                break

        return name

    #------------------------------------------------------------
    def _start_new_log(self, config_file, rownum):
        '''
        Starting a new log definition in self.new_log and filling it
        with the current default values.

        @param config_file: the configuration file with the start
                            of the logfile definition
        @type config_file:  str
        @param rownum:      the row number of the configuration file
                            with the start of the logfile definition
        @type rownum:       int
        '''

        if self.verbose > 3:
            msg = _("Starting a new log directive with default values.")
            LOG.debug(msg)

        self.new_log = {}

        self.new_log['files'] = []
        self.new_log['file_patterns'] = []

        self.new_log['compress']      = self.default['compress']
        self.new_log['compresscmd']   = self.default['compresscmd']
        self.new_log['compressext']   = self.default['compressext']
        self.new_log['compressoptions']  = self.default['compressoptions']
        self.new_log['configfile']    = config_file
        self.new_log['configrow']     = rownum
        self.new_log['copy']          = self.default['copy']
        self.new_log['copytruncate']  = self.default['copytruncate']
        self.new_log['create']        = {
            'enabled': self.default['create']['enabled'],
            'mode':    self.default['create']['mode'],
            'owner':   self.default['create']['owner'],
            'group':   self.default['create']['group'],
        }
        self.new_log['period']        = self.default['period']
        self.new_log['dateext']       = self.default['dateext']
        self.new_log['datepattern']   = self.default['datepattern']
        self.new_log['delaycompress'] = self.default['delaycompress']
        self.new_log['extension']     = self.default['extension']
        self.new_log['ifempty']       = self.default['ifempty']
        self.new_log['mailaddress']   = self.default['mailaddress']
        self.new_log['mailfirst']     = self.default['mailfirst']
        self.new_log['maxage']        = self.default['maxage']
        self.new_log['missingok']     = self.default['missingok']
        self.new_log['olddir']        = {
            'dirname':    self.default['olddir']['dirname'],
            'dateformat': self.default['olddir']['dateformat'],
            'enabled':    self.default['olddir']['enabled'],
            'mode':       self.default['olddir']['mode'],
            'owner':      self.default['olddir']['owner'],
            'group':      self.default['olddir']['group'],
        }
        self.new_log['rotate']        = self.default['rotate']
        self.new_log['sharedscripts'] = self.default['sharedscripts']
        self.new_log['shred']         = self.default['shred']
        self.new_log['size']          = self.default['size']
        self.new_log['start']         = self.default['start']

        for script_type in script_directives:
            self.new_log[script_type] = None

    #------------------------------------------------------------
    def _assign_logfiles(self):
        '''
        Finds all existing logfiles of self.new_log according to the
        shell matching patterns in self.new_log['file_patterns'].
        If a logfile was even defined, a warning is omitted and the
        new definition will thrown away.

        @return: number of found logfiles according
                 to self.new_log['file_patterns']
        @rtype:  int
        '''

        if len(self.new_log['file_patterns']) <= 0:
            msg = _("No logfile pattern defined.")
            LOG.warning(msg)
            return 0

        for pattern in self.new_log['file_patterns']:
            if self.verbose > 1:
                msg = _("Find all logfiles for shell matching "
                         + "pattern '%s' ...") \
                       % (pattern)
                LOG.debug(msg)
            logfiles = glob.glob(pattern)
            if len(logfiles) <= 0:
                msg = _("No logfile found for pattern '%s'.") % (pattern)
                if self.new_log['missingok']:
                    LOG.debug(msg)
                else:
                    LOG.warning(msg)
                continue
            for logfile in logfiles:
                if self.verbose > 1:
                    msg = (_("Found logfile '%(file)s for pattern " +
                             "'%(pattern)s'.")
                           % {'file': logfile, 'pattern': pattern })
                    LOG.debug(msg)
                if logfile in self.defined_logfiles:
                    f = self.defined_logfiles[logfile]
                    msg = ( _("Logfile '%(logfile)s' is even defined "
                                + "(file '%(cfgfile)s', row %(rownum)d) "
                                + "and so not taken a second time.") 
                             % {'logfile': logfile,
                                'cfgfile': f['file'],
                                'rownum': f['rownum']}
                    )
                    LOG.warning(msg)
                    continue
                if self.verbose > 1:
                    msg = _("Logfile '%s' will taken.") % (logfile)
                self.defined_logfiles[logfile] = {
                        'file': self.new_log['configfile'],
                        'rownum': self.new_log['configrow'],
                }
                self.new_log['files'].append(logfile)

        return len(self.new_log['files'])

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
