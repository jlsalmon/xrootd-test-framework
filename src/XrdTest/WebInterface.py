#!/usr/bin/env python
#-------------------------------------------------------------------------------
#
# Copyright (c) 2011-2012 by European Organization for Nuclear Research (CERN)
# Author: Justin Salmon <jsalmon@cern.ch>
#
# This file is part of XrdTest.
#
# XrdTest is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# XrdTest is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with XrdTest.  If not, see <http://www.gnu.org/licenses/>.
#
#-------------------------------------------------------------------------------
#
# File:    WebInterface
# Desc:    TODO:
#-------------------------------------------------------------------------------
from Utils import get_logger
LOGGER = get_logger(__name__)

import sys
import os
import socket

try:
    import cherrypy
    from Cheetah.Template import Template
    from cherrypy.lib.static import serve_file
except ImportError, e:
    LOGGER.error(str(e))
    sys.exit(1)


class WebInterface:
    '''
    All pages and files available via Web Interface,
    defined as methods of this class.
    '''
    def __init__(self, config, test_master_ref):
        # reference to XrdTestMaster main object
        self.testMaster = test_master_ref
        # reference to loaded config
        self.config = config

        self.cp_config = {'request.error_response': handleCherrypyError,
                          'error_page.404': \
                          self.config.get('webserver', 'webpage_dir') + \
                          os.sep + "page_404.tmpl"}

    def disp(self, tpl_file, tpl_vars):
        '''
        Utility method for displying tpl_file and replace tpl_vars.

        @param tpl_file: to be displayed as HTML page
        @param tpl_vars: vars can be used in HTML page, Cheetah style
        '''
        tpl = None
        tplFile = self.config.get('webserver', 'webpage_dir') \
                    + os.sep + tpl_file

        tpl_vars['HTTPport'] = self.config.getint('webserver', 'port')
        try:
            tpl = Template(file=tplFile, searchList=[tpl_vars])
        except Exception, e:
            LOGGER.error(str(e))
            return "An error occured. Check log for details."
        else:
            return tpl.respond()

    def index(self):
        '''
        Main page of web interface, shows definitions.
        '''
        tplVars = { 'title' : 'Xrd Test Master - Web Interface',
                    'message' : 'Welcome and begin the tests!',
                    'clusters' : self.testMaster.clusters,
                    'hypervisors': self.testMaster.hypervisors,
                    'suitsSessions' : self.testMaster.suiteSessions,
                    'runningSuitsUids' : self.testMaster.runningSuiteUids,
                    'slaves': self.testMaster.slaves,
                    'hostname': socket.gethostname(),
                    'testSuits': self.testMaster.testSuites,
                    'userMsgs' : self.testMaster.userMsgs,
                    'testMaster': self.testMaster, }
        return self.disp("main.tmpl", tplVars)

    def suiteSessions(self):
        '''
        Page showing suit sessions runs.
        '''
        tplVars = { 'title' : 'Xrd Test Master - Web Iface',
                    'suitsSessions' : self.testMaster.suiteSessions,
                    'runningSuitsUids' : self.testMaster.runningSuiteUids,
                    'slaves': self.testMaster.slaves,
                    'hostname': socket.gethostname(),
                    'testSuits': self.testMaster.testSuites,
                    'testMaster': self.testMaster,
                    'HTTPport' : self.config.getint('webserver', 'port')}
        return self.disp("suits_sessions.tmpl", tplVars)

    def indexRedirect(self):
        '''
        Page that at once redirects user to index. Used to clear URL parameters.
        '''
        tplVars = { 'hostname': socket.gethostname(),
                    'HTTPport': self.config.getint('webserver', 'port')}
        return self.disp("index_redirect.tmpl", tplVars)

    def downloadScript(self, script_name):
        '''
        Enable slave to download some script as a regular FILE from masters
        scripts (WEBPAGE_DIR/scripts dir) and run it.
        @param script_name:
        '''
        #from xml.sax.saxutils import quoteattr
        p = self.config.get('webserver', 'webpage_dir') \
                + os.sep + 'scripts' + os.sep + script_name

        if os.path.exists(p):
            return serve_file(p , "application/x-download", "attachment")
        else:
            return "%s: not found at %s" % (script_name, p)

    def showScript(self, script_name):
        '''
        Enable slave to view some script as TEXT from masters
        scripts (WEBPAGE_DIR/scripts dir) and run it.
        @param script_name:
        '''
        #from xml.sax.saxutils import quoteattr
        p = self.config.get('webserver', 'webpage_dir') \
                          + os.sep + 'scripts' + os.sep + \
                          script_name
        if os.path.exists(p):
            return serve_file(p , "text/html")
        else:
            return "%s: not found at %s" % (script_name, p)
        

    index.exposed = True
    suiteSessions.exposed = True
    downloadScript.exposed = True
    showScript.exposed = True
    

def handleCherrypyError():
        cherrypy.response.status = 500
        cherrypy.response.body = \
                        ["An error occured. Check log for details."]
        LOGGER.error("Cherrypy error: " + \
                     str(cherrypy._cperror.format_exc(None)))
    
