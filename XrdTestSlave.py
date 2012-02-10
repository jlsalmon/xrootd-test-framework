#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Author:  Lukasz Trzaska <ltrzaska@cern.ch>
# Date:    
# File:    XrdTestHypervisor
# Desc:    Xroot Testing Framework Hypervisor component.
#-------------------------------------------------------------------------------
# Logging settings
#-------------------------------------------------------------------------------
import copy
import logging
import sys

logging.basicConfig(format='%(asctime)s %(levelname)s ' + \
                    '[%(filename)s %(lineno)d] ' + \
                    '%(message)s', level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.debug("Running script: " + __file__)
#------------------------------------------------------------------------------ 
try:
    from Daemon import Daemon, readConfig, DaemonException, Runnable
    from SocketUtils import FixedSockStream, XrdMessage, SocketDisconnectedError
    from TestUtils import TestSuite
    from Utils import State
    from optparse import OptionParser
    from string import join, replace
    from subprocess import Popen
    import ConfigParser
    import Queue
    import os
    import socket
    import ssl
    import subprocess
    import threading
except ImportError, e:
    LOGGER.error(str(e))
    sys.exit(1)
#------------------------------------------------------------------------------ 
# Globals and configurations
currentDir = os.path.dirname(os.path.abspath(__file__))
os.chdir(currentDir)
#Default daemon configuration
defaultConfFile = './XrdTestSlave.conf'
defaultPidFile = '/var/run/XrdTestSlave.pid'
defaultLogFile = '/var/log/XrdTest/XrdTestSlave.log'

#-------------------------------------------------------------------------------
class TCPReceiveThread(object):
    #---------------------------------------------------------------------------
    def __init__(self, sock, recvQueue):
        '''
        @param sock:
        @param recvQueue:
        '''
        self.sockStream = sock
        self.stopEvent = threading.Event()
        self.stopEvent.clear()
        self.recvQueue = recvQueue
    #---------------------------------------------------------------------------
    def close(self):
        self.stopEvent.set()
    #---------------------------------------------------------------------------
    def run(self):
        while not self.stopEvent.isSet():
            try:
                msg = self.sockStream.recv()
                LOGGER.debug("Received raw: " + str(msg))
                self.recvQueue.put(msg)
            except SocketDisconnectedError, e:
                LOGGER.info("Connection to XrdTestMaster closed.")
                sys.exit(1)
                break
#-------------------------------------------------------------------------------
class XrdTestSlave(Runnable):
    '''
    Test Slave main executable class.
    '''
    sockStream = None
    recvQueue = Queue.Queue()
    config = None
    #---------------------------------------------------------------------------
    def __init__(self, config):
        self.sockStream = None
        #Blocking queue of commands received from XrdTestMaster
        self.recvQueue = Queue.Queue()
        self.config = config
        self.stopEvent = threading.Event()
    #---------------------------------------------------------------------------
    def executeSh(self, cmd):
        '''
        @param cmd:
        '''
        global LOGGER

        command = ""

        LOGGER.info("executeSh: %s" % cmd)
        #reading a file contents
        if cmd[0:2] == "#!":
            LOGGER.info("Direct shell script to be executed.")
            command = cmd
        else:
            import urllib
            f = urllib.urlopen(cmd)
            lines = f.readlines()
            f.close()
            command = join(lines, "\n")

            if "http:" in cmd:
                LOGGER.info("Loaded script from url: " + cmd)
            else:
                LOGGER.info("Running script from file: " + cmd)

        command = command.replace("@slavename@", socket.gethostname())
        LOGGER.info("Shell script to run: " + command)

        res = None
        try:
            process = Popen(command, shell="None", \
                        stdout=subprocess.PIPE, \
                        stderr=subprocess.PIPE)

            stdout, stderr = process.communicate()
            res = (stdout, stderr, str(process.returncode))
        except ValueError, e:
            LOGGER.exception("Execution of shell script failed:" + str(e))
        except OSError, e:
            LOGGER.exception("Execution of shell script failed:" + str(e))
        return res
    #---------------------------------------------------------------------------
    def connectMaster(self, masterIp, masterPort):
        global currentDir
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sockStream = ssl.wrap_socket(sock, server_side=False,
                                        certfile=\
                                        self.config.get('security', 'certfile'),
                                        keyfile=\
                                        self.config.get('security', 'keyfile'),
                                        ssl_version=ssl.PROTOCOL_TLSv1)
            #self.sockStream = sock
            self.sockStream.connect((masterIp, masterPort))
        except socket.error, e:
            if e[0] == 111:
                LOGGER.info("Connection from master refused.")
            else:
                LOGGER.info("Connection with master could not be established.")
                LOGGER.exception(e)
            return None
        else:
            LOGGER.debug("Connected to master.")
        try:
            self.sockStream = FixedSockStream(self.sockStream)

            #authenticate in master
            self.sockStream.send(\
                self.config.get('test_master', 'connection_passwd'))
            msg = self.sockStream.recv()
            LOGGER.info('Received msg: ' + msg)
            if msg == "PASSWD_OK":
                LOGGER.info("Connected and authenticated to XrdTestMaster " + \
                            "successfully. Waiting for commands " + \
                            "from the master.")
            else:
                LOGGER.info("Password authentication in master failed.")
                return None
        except socket.error, e:
            LOGGER.exception(e)
            return None

        self.sockStream.send(("slave", socket.gethostname()))

        return self.sockStream
    #---------------------------------------------------------------------------
    def handleRunTestCase(self, msg):
        suiteName = msg.suiteName
        testName = msg.testName
        testUid = msg.testUid
        case = msg.case

        msg = XrdMessage(XrdMessage.M_TESTSUITE_STATE)
        msg.state = State(TestSuite.S_TESTCASE_INITIALIZED)
        msg.testUid = testUid
        msg.suiteName = suiteName
        msg.testName = testName

        msg.result = self.executeSh(case.initialize)

        LOGGER.info("Executed testCase.initialize() %s [%s] with result %s:" % \
                    (testName, suiteName, msg.result))
        self.sockStream.send(msg)

        msg2 = copy.copy(msg)
        msg2.result = self.executeSh(case.run)
        if int(msg2.result[2]) < 0:
            msg2.state = State(TestSuite.S_TESTCASE_RUNFINISHED_ERROR)
        else:
            msg2.state = State(TestSuite.S_TESTCASE_RUNFINISHED)
        self.sockStream.send(msg2)

        LOGGER.info("Executed testCase.run() %s [%s] with result %s:" % \
                    (testName, suiteName, msg2.result))

        msg3 = copy.copy(msg)
        msg3.testName = testName
        msg3.result = self.executeSh(case.finalize)
        msg3.state = State(TestSuite.S_TESTCASE_FINALIZED)

        LOGGER.info("Executed testCase.finalize() %s [%s] with result %s:" % \
            (testName, suiteName, msg2.result))

        return msg3
    #---------------------------------------------------------------------------
    def handleTestSuiteInitialize(self, msg):
        cmd = msg.cmd
        suiteName = msg.suiteName
        
        msg = XrdMessage(XrdMessage.M_TESTSUITE_STATE)
        msg.state = State(TestSuite.S_SLAVE_INITIALIZED)
        msg.suiteName = suiteName
        msg.result = self.executeSh(cmd)

        return msg
    #---------------------------------------------------------------------------
    def handleTestSuiteFinalize(self, msg):
        cmd = msg.cmd
        suiteName = msg.suiteName
        
        msg = XrdMessage(XrdMessage.M_TESTSUITE_STATE)
        msg.state = State(TestSuite.S_SLAVE_FINALIZED)
        msg.suiteName = suiteName
        msg.result = self.executeSh(cmd)

        return msg
    #---------------------------------------------------------------------------
    def recvLoop(self):
        global LOGGER
        while not self.stopEvent.isSet():
            try:
                #receive msg from master
                msg = self.recvQueue.get()
                LOGGER.info("Received msg: " + str(msg.name))

                resp = XrdMessage(XrdMessage.M_UNKNOWN)
                if msg.name is XrdMessage.M_HELLO:
                    resp = XrdMessage(XrdMessage.M_HELLO)
                elif msg.name == XrdMessage.M_TESTSUITE_INIT:
                    resp = self.handleTestSuiteInitialize(msg)
                elif msg.name == XrdMessage.M_TESTSUITE_FINALIZE:
                    resp = self.handleTestSuiteFinalize(msg)
                elif msg.name == XrdMessage.M_TESTCASE_RUN:
                    resp = self.handleRunTestCase(msg)
                else:
                    LOGGER.info("Received unknown message: " + str(msg.name))
                self.sockStream.send(resp)
                LOGGER.debug("Sent msg: " + str(resp))
            except SocketDisconnectedError:
                LOGGER.info("Connection to XrdTestMaster closed.")
                sys.exit()
                break
    #---------------------------------------------------------------------------
    def run(self):
        sock = self.connectMaster(self.config.get('test_master', 'ip'),
                           self.config.getint('test_master', 'port'))
        if not sock:
            return

        tcpReceiveTh = TCPReceiveThread(self.sockStream, self.recvQueue)
        thTcpReceive = threading.Thread(target=tcpReceiveTh.run)
        thTcpReceive.start()
	
        self.recvLoop()

#-------------------------------------------------------------------------------
def main():
    '''
    Program begins here.
    '''
    parse = OptionParser()
    parse.add_option("-c", "--configfile", dest="configFile", type="string", \
                     action="store", help="config (.conf) file location")
    parse.add_option("-b", "--background", dest="backgroundMode", \
                     type="string", action="store", \
                      help="run runnable as a daemon")

    (options, args) = parse.parse_args()

    isConfigFileRead = False
    config = ConfigParser.ConfigParser()
    #---------------------------------------------------------------------------
    # read the config file
    #---------------------------------------------------------------------------
    global defaultConfFile
    LOGGER.info("Loading config file: %s" % options.configFile)
    try:
        confFile = ''
        if options.configFile:
            confFile = options.configFile
        if not os.path.exists(confFile):
            confFile = defaultConfFile
        config = readConfig(confFile)
        isConfigFileRead = True
    except (RuntimeError, ValueError, IOError), e:
        LOGGER.exception()
        sys.exit(1)

    testSlave = XrdTestSlave(config)
    #--------------------------------------------------------------------------
    # run the daemon
    #--------------------------------------------------------------------------
    if options.backgroundMode:
        LOGGER.info("Run in background: %s" % options.backgroundMode)

        pidFile = defaultPidFile
        logFile = defaultLogFile
        if isConfigFileRead:
            pidFile = config.get('daemon', 'pid_file_path')
            logFile = config.get('daemon', 'log_file_path')

        dm = Daemon("XrdTestSlave.py", pidFile, logFile)
        try:
            if options.backgroundMode == 'start':
                dm.start(testSlave)
            elif options.backgroundMode == 'stop':
                dm.stop()
            elif options.backgroundMode == 'check':
                res = dm.check()
                print 'Result of runnable check: %s' % str(res)
            elif options.backgroundMode == 'reload':
                dm.reload()
                print 'You can either start, stop, check or reload the deamon'
                sys.exit(3)
        except (DaemonException, RuntimeError, ValueError, IOError), e:
            LOGGER.error(str(e))
            sys.exit(1)
    #--------------------------------------------------------------------------
    # run test master in standard mode. Used for debugging
    #--------------------------------------------------------------------------
    if not options.backgroundMode:
        testSlave.run()
#-------------------------------------------------------------------------------
# Start place
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
