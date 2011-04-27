#!/usr/bin/env python
# -*- coding: utf-8 -*-

# $Id$
# $URL$

'''
@author: Frank Brehm
@contact: frank@brehm-online.com
@license: GPL3
@copyright: (c) 2010-2011 by Frank Brehm, Berlin
@version: 0.0.2
@summary: module the configuration parsing object for Python logrotating
'''

import re
import sys
import gettext
import pprint
import os
import os.path

revision = '$Revision$'
revision = re.sub( r'\$', '', revision )
revision = re.sub( r'Revision: ', r'r', revision )
revision = re.sub( r'\s*$', '', revision )

__author__    = 'Frank Brehm'
__copyright__ = '(C) 2011 by Frank Brehm, Berlin'
__contact__    = 'frank@brehm-online.com'
__version__    = '0.0.2 ' + revision
__license__    = 'GPL3'


#========================================================================
# Module variables

# @var: dict with all valid taboo pattern types as keys
#       and the resulting regex template for the filename as value
pattern_types = {
    'ext':    r'%s$',
    'file':   r'^%s$',
    'prefix': r'^%s',
}

#========================================================================

class LogrotateConfigurationError(Exception):
    '''
    Base class for exceptions in this module.
    '''

#========================================================================

class LogrotateConfigurationReader(object):
    '''
    Class for reading the configuration for Python logrotating

    @author: Frank Brehm
    @contact: frank@brehm-online.com
    '''

    #-------------------------------------------------------
    def __init__( self, config_file,
                        verbose    = 0,
                        logger     = None,
                        local_dir  = None,
    ):
        '''
        Costructor.

        @param config_file: the configuration file to use
        @type config_file:  str
        @param verbose:     verbosity (debug) level
        @type verbose:      int
        @param logger:      logger object to use for logging a.s.o.
        @type logger:       logging.getLogger or None
        @param local_dir:   The directory, where the i18n-files (*.mo)
                            are located. If None, then system default
                            (/usr/share/locale) is used.
        @type local_dir:    str or None

        @return: None
        '''

        self.local_dir = local_dir
        '''
        @ivar: The directory, where the i18n-files (*.mo) are located.
        @type: str or None
        '''

        self.t = gettext.translation(
            'LogRotateConfig',
            local_dir,
            fallback = True
        )
        '''
        @ivar: a gettext translation object
        @type: gettext.translation
        '''

        _ = self.t.lgettext

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

        self.logger = logger
        '''
        @ivar: logger object
        @type: logging.getLogger
        '''

        if not logger:

            #################################################
            # Create a logger object, if necessary
            self.logger = logging.getLogger('logrotate_cfg')

            self.logger.setLevel(logging.DEBUG)

            pp = pprint.PrettyPrinter(indent=4)
            # create console handler and set level to debug
            ch = logging.StreamHandler()
            #ch.setLevel(logging.DEBUG)
            if verbose:
                ch.setLevel(logging.DEBUG)
            else:
                ch.setLevel(logging.INFO)

            # create formatter
            formatter = logging.Formatter(
                '[%(asctime)s]: %(name)s %(levelname)-8s - %(message)s'
            )

            # add formatter to ch
            ch.setFormatter(formatter)

            # add ch to logger
            self.logger.addHandler(ch)

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

        self.scripts = []
        '''
        @ivar: list of all named scripts found in configuration
        @type: list
        '''

        self.logger.debug( _("Logrotate config reader initialised") )

    #------------------------------------------------------------
    def __str__(self):
        '''
        Typecasting function for translating object structure
        into a string

        @return: structure as string
        @rtype:  str
        '''

        pp = pprint.PrettyPrinter(indent=4)
        structure = {
            'config':          self.config,
            'config_file':     self.config_file,
            'config_files':    self.config_files,
            'config_was_read': self.config_was_read,
            'default':         self.default,
            'new_log':         self.new_log,
            'local_dir':       self.local_dir,
            'search_path':     self.search_path,
            'scripts':         self.scripts,
            'shred_command':   self.shred_command,
            'taboo':           self.taboo,
            'verbose':         self.verbose,
        }
        return pp.pformat(structure)

    #------------------------------------------------------------
    def _reset_defaults(self):
        '''
        Resetting self.default to the hard coded values
        '''

        _ = self.t.lgettext

        if self.verbose > 3:
            self.logger.debug( _("Resetting default values for directives "
                    + "to hard coded values")
            )

        self.default = {}

        self.default['compress']      = False
        self.default['compress_cmd']  = 'internal_gzip'
        self.default['compress_ext']  = None
        self.default['compress_opts'] = None
        self.default['copy']          = False
        self.default['copytruncate']  = False
        self.default['create']        = {
            'mode':  None,
            'owner': None,
            'group': None,
        },
        self.default['period']        = 7
        self.default['dateext']       = False
        self.default['datepattern']   = '%Y-%m-%d'
        self.default['delaycompress'] = False
        self.default['extension']     = ""
        self.default['ifempty']       = True
        self.default['mailaddress']   = None
        self.default['mailfirst']     = None
        self.default['maxage']        = None
        self.default['missingok']     = False
        self.default['olddir']        = {
            'dirname':    '',
            'dateformat': False,
            'mode':       None,
            'owner':      None,
            'group':      None,
        },
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

        _ = self.t.lgettext

        if not pattern_type in pattern_types:
            raise Exception( _('Invalid pattern type "%s" given') % (pattern_type) )

        pattern = ( pattern_types[pattern_type] % pattern )
        if self.verbose > 3:
            self.logger.debug( _("New taboo pattern: '%s'.") % (pattern) )

        self.taboo.append(pattern)

    #------------------------------------------------------------
    def _init_search_path(self):
        '''
        Initialises the internal list of search pathes

        @return: None
        '''

        _ = self.t.lgettext
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
                    self.logger.debug(
                        _("'%s' is not a directory") % (item)
                    )
                        
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
                    self.logger.debug(
                        _("'%s' is not a directory") % (item)
                    )

        # Including own defined directories
        for item in ('/usr/local/bin', '/sbin', '/usr/sbin', '/usr/local/sbin'):
            if os.path.isdir(item):
                real_dir = os.path.abspath(item)
                if not real_dir in dir_included:
                    path_list.append(real_dir)
                    dir_included[real_dir] = True
            else:
                self.logger.debug(
                    _("'%s' is not a directory") % (item)
                )

        self.search_path = path_list

    #------------------------------------------------------------
    def _get_std_search_path(self, include_current = False):
        '''
        Returns a list with all search directories from $PATH and some additionally
        directiories.

        @param include_current: include the current working directory
                                at the end of the list
        @type include_current:  bool

        @return: list of search directories
        @rtype:  list
        '''

        #_ = self.t.lgettext

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

        _ = self.t.lgettext
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
                self.logger.debug( _("Search path '%s' doesn't exists "
                                      + "or is not a directory")
                                   % (search_dir)
                )

        if found:
            self.logger.debug( _("Shred command found: '%s'") %(cmd) )
            self.shred_command = cmd
            return True
        else:
            self.logger.warning( _("Shred command not found, shred disabled") )
            self.shred_command = None
            return False

    #------------------------------------------------------------
    def check_compress_command(self, command):
        '''
        Checks the availability of the given compress command.

        'internal_gzip' and 'internal_bzip2' are accepted as valid compress
        commands for compressing with the appropriate python modules.

        @param command: command to validate (absolute or relative for
                        searching in standard search path)
        @type command:  str

        @return: absolute path of the compress command, 'internal_gzip',
                 'internal_bzip2' or None if not found or invalid
        @rtype:  str or None
        '''

        _ = self.t.lgettext
        path_list = self._get_std_search_path(True)

        match = re.search(r'^\s*internal[\-_\s]?gzip\s*', command, re.IGNORECASE)
        if match:
            return 'internal_gzip'

        match = re.search(r'^\s*internal[\-_\s]?bzip2\s*', command, re.IGNORECASE)
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
                self.logger.debug( _("Search path '%s' doesn't exists "
                                      + "or is not a directory")
                                   % (search_dir)
                )

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

        if not self.config_was_read:
            if not self._read():
                return None

        return self.config

    #------------------------------------------------------------
    def get_scripts(self):
        '''
        Returns the scriptlist, how it was read from configuration file(s)

        @return: list of scripts
        @rtype:  list
        '''

        if not self.config_was_read:
            if not self._read():
                return None

        return self.scripts

    #------------------------------------------------------------
    def _read(self):
        '''
        Reads the configuration from configuration file and all
        included files
        '''

        _ = self.t.lgettext
        self.logger.debug( _("Try reading configuration from '%s' ...")
                            % (self.config_file) )

        if not os.path.exists(self.config_file):
            raise LogrotateConfigurationError(
                _("File '%s' doesn't exists.") % (self.config_file)
            )

        self.config_file = os.path.abspath(self.config_file)

        if not os.path.isfile(self.config_file):
            raise LogrotateConfigurationError(
                _("'%s' is not a regular file.") % (self.config_file)
            )

        self.config_files[self.config_file] = True

        self.logger.info( _("Reading configuration from '%s' ...")
                            % (self.config_file) )

        cfile = None
        try:
            cfile = open(self.config_file, 'Ur')
        except IOError, e:
            raise LogrotateConfigurationError(
                ( _("Could not read configuration file '%s'")
                    % (self.config_file) )
                + ': ' + str(e)
            )
        lines = cfile.readlines()
        cfile.close()

        # defaults for the big loop
        linenr    = 0
        in_fd     = False
        in_script = False
        lastrow   = ''
        newscript = ''

        # inspect every line of configuration file
        for line in lines:

            linenr += 1
            line = line.strip()

            # Perform a bckslash at the end of the line
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
                self.scripts[newscript].append(line)
                continue

            # start of a logfile pattern
            match = re.search(r'^[\'"]', line)
            if match or os.path.isabs(line):
                parts = self._split_parts(line)

        return True

    #------------------------------------------------------------
    def _start_new_log(self):
        '''
        Starting a new log definition in self.new_log and filling it
        with the current default values.
        '''

        _ = self.t.lgettext

        if self.verbose > 3:
            self.logger.debug(
                _("Starting a new log directive with default values")
            )

        self.new_log = {}

        self.new_log['file_patterns'] = []

        self.new_log['compress']      = self.default['compress']
        self.new_log['compress_cmd']  = self.default['compress_cmd']
        self.new_log['compress_ext']  = self.default['compress_ext']
        self.new_log['compress_opts'] = self.default['compress_opts']
        self.new_log['copy']          = self.default['copy']
        self.new_log['copytruncate']  = self.default['copytruncate']
        self.new_log['create']        = {
            'mode':  self.default['create']['mode'],
            'owner': self.default['create']['owner'],
            'group': self.default['create']['group'],
        },
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
            'mode':       self.default['olddir']['mode'],
            'owner':      self.default['olddir']['owner'],
            'group':      self.default['olddir']['group'],
        },
        self.new_log['rotate']        = self.default['rotate']
        self.new_log['shred']         = self.default['shred']
        self.new_log['size']          = self.default['size']
        self.new_log['start']         = self.default['start']

    #------------------------------------------------------------
    def _split_parts(self, text):
        '''
        Split the given text in chunks by whitespaces or
        single or double quoted strings.
        
        @param text: the text to split in chunks
        @type text:  str

        @return: list of chunks
        @rtype:  list
        '''

        chunks = []
        if text is None:
            return chunks

        txt = str(text)
        last_chunk = ''

        # Big loop to split the text - until it is empty
        while txt != '':

            # add chunk, if there is a chunk left and a whitspace
            # at the begin of the line
            match = re.search(r"\s+", txt)
            if ( last_chunk != '' ) and match:
                chunks.append(last_chunk)
                last_chunk = ''

            # clean the line
            txt = txt.strip()
            if txt == '':
                break

            # search for a single quoted string at the begin of the line
            match = re.search(r"^'((?:\\'|[^'])*)'", txt)
            if match:
                last_chunk += match.group(1)
                txt = re.sub(r"^'(?:\\'|[^'])*'", "", txt)
                continue

            # search for a double quoted string at the begin of the line
            match = re.search(r'^"((?:\\"|[^"])*)"', txt)
            if match:
                last_chunk += match.group(1)
                txt = re.sub(r'^"(?:\\"|[^"])*"', "", txt)
                continue

            # search for unquoted, whitespace delimited text
            # at the begin of the line
            match = re.search(r'^([^\s\'"]+)', txt)
            if match:
                last_chunk += match.group(1)
                txt = re.sub(r'^[^\s\'"]+', "", txt)
                continue

            # Only whitespaces left
            match = re.search(r'^\s*$', txt)
            if match:
                break

            # Here we should not come to ...
            raise Exception("Broken split of »%s«: »%s« left" %( str(text), txt))

        if last_chunk != '':
            chunks.append(last_chunk)

        _ = self.t.lgettext
        pp = pprint.PrettyPrinter(indent=4)

        if self.verbose > 3:
            self.logger.debug(
                ( _("Split into chunks of: »%s«") % (str(text)))
                + ":\n" + pp.pformat(chunks)
            )

        return chunks

#========================================================================

if __name__ == "__main__":
    pass


#========================================================================

# vim: fileencoding=utf-8 filetype=python ts=4 expandtab
