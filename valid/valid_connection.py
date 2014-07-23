"""
L{ValidConnection}.
"""

import paramiko
import re
import sys
import time
import subprocess
import os
import random
import string
import logging
import socket
import select
import SocketServer
import threading


class ValidConnectionException(Exception):
    """ StitchesConnection Exception """
    pass


def lazyprop(func):
    """ Create lazy property """
    attr_name = '_lazy_' + func.__name__

    @property
    def _lazyprop(self):
        """ Create lazy property """
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)
    return _lazyprop


class ValidConnection(object):
    """
    Stateful object to represent connection to the host
    """
    def __init__(self, hostname, username="root", key_filename=None,
                 timeout=10, output_shell=False):
        """
        Create connection object

        @param hostname: hostname or ip address
        @type hostname: str

        @param username: user name for creating ssh connection
        @type username: str

        @param key_filename: file name with ssh private key
        @type key_filename: str

        @param timeout: timeout for creating ssh connection
        @type timeout: int

        @param output_shell: write output from this connection to standard
                             output
        @type output_shell: bool
        """
        self.logger = logging.getLogger('valid.connection')

        self.hostname = hostname
        self.username = username
        self.key_filename = key_filename
        self.output_shell = output_shell
        self.timeout = timeout

        # debugging buffers
        self.last_command = ""
        self.last_stdout = ""
        self.last_stderr = ""

        if key_filename:
            self.look_for_keys = False
        else:
            self.look_for_keys = True

        self.forwardthread = None
        self.forwardport = None
        self.stdin_rpyc, self.stdout_rpyc, self.stderr_rpyc = None, None, None

        logging.getLogger("paramiko").setLevel(logging.WARNING)

    @lazyprop
    def cli(self):
        """ cli lazy property """
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        client.connect(hostname=self.hostname,
                       username=self.username,
                       key_filename=self.key_filename,
                       timeout=self.timeout,
                       look_for_keys=self.look_for_keys)
        # set keepalive
        transport = client.get_transport()
        transport.set_keepalive(3)
        return client

    @lazyprop
    def channel(self):
        """ channel lazy property """
        # start shell, non-blocking channel
        chan = self.cli.invoke_shell(width=360, height=80)
        chan.setblocking(0)
        # set channel timeout
        chan.settimeout(10)
        # now waiting for shell prompt ('username@')
        result = ""
        count = 0
        while count < 10:
            try:
                recv_part = chan.recv(16384)
                result += recv_part
            except socket.timeout:
                # socket.timeout here means 'no more data'
                pass

            if result.find('%s@' % self.username) != -1:
                return chan
            time.sleep(1)
            count += 1
        # failed to get shell prompt on channel :-(
        raise ValidConnectionException("Failed to get shell prompt")

    @lazyprop
    def sftp(self):
        """ sftp lazy property """
        return self.cli.open_sftp()

    @lazyprop
    def rpyc(self):
        """ RPyC lazy property """
        try:
            import rpyc

            devnull_fd = open("/dev/null", "w")
            rpyc_dirname = os.path.dirname(rpyc.__file__)
            rnd_id = ''.join(random.choice(string.ascii_lowercase) for x in range(10))
            pid_filename = "/tmp/%s.pid" % rnd_id
            pid_dest_filename = "/tmp/%s%s.pid" % (rnd_id, rnd_id)
            rnd_filename = "/tmp/" + rnd_id + ".tar.gz"
            rnd_dest_filename = "/tmp/" + rnd_id + rnd_id + ".tar.gz"
            subprocess.check_call(["tar", "-cz", "--exclude", "*.pyc", "--exclude", "*.pyo", "--transform",
                                   "s,%s,%s," % (rpyc_dirname[1:][:-5], rnd_id), rpyc_dirname, "-f", rnd_filename],
                                  stdout=devnull_fd, stderr=devnull_fd)
            devnull_fd.close()

            self.sftp.put(rnd_filename, rnd_dest_filename)
            os.remove(rnd_filename)
            self.recv_exit_status("tar -zxvf %s -C /tmp" % rnd_dest_filename, 10)

            server_script = r"""
import os
print os.environ
from rpyc.utils.server import ThreadedServer
from rpyc import SlaveService
import sys
t = ThreadedServer(SlaveService, hostname = 'localhost', port = 0, reuse_addr = True)
fd = open('""" + pid_filename + r"""', 'w')
fd.write(str(t.port))
fd.close()
t.start()
"""
            command = "echo \"%s\" | PYTHONPATH=\"/tmp/%s\" python " % (server_script, rnd_id)
            self.stdin_rpyc, self.stdout_rpyc, self.stderr_rpyc = self.exec_command(command, get_pty=True)
            self.recv_exit_status("while [ ! -f %s ]; do sleep 1; done" % (pid_filename), 10)
            self.sftp.get(pid_filename, pid_dest_filename)
            pid_fd = open(pid_dest_filename, 'r')
            port = int(pid_fd.read())
            pid_fd.close()
            os.remove(pid_dest_filename)
            self.forwardport = self.forward_tunnel(0, 'localhost', port)

            return rpyc.classic.connect('localhost', self.forwardport)

        except Exception, err:
            self.logger.debug("Failed to setup rpyc: %s" % err)
            return None

    def reconnect(self):
        """
        Close the connection and open a new one
        """
        self.disconnect()

    def disconnect(self):
        """
        Close the connection
        """
        if hasattr(self, '_lazy_sftp'):
            self.sftp.close()
            delattr(self, '_lazy_sftp')
        if hasattr(self, '_lazy_channel'):
            self.channel.close()
            delattr(self, '_lazy_channel')
        if hasattr(self, '_lazy_cli'):
            self.cli.close()
            delattr(self, '_lazy_cli')
        if hasattr(self, '_lazy_rpyc'):
            self.rpyc.close()
            delattr(self, '_lazy_rpyc')
        if self.forwardthread and self.forwardport:
            # do empty request to make 'handle_request' succeed
            socket.create_connection(('localhost', self.forwardport))
            # join forwarder thread
            self.forwardthread.join(self.timeout)
            self.forwardthread = None
            self.forwardport = None

    def exec_command(self, command, bufsize=-1, get_pty=False):
        """
        Execute a command in the connection

        @param command: command to execute
        @type command: str

        @param bufsize: buffer size
        @type bufsize: int

        @param get_pty: get pty
        @type get_pty: bool

        @return: the stdin, stdout, and stderr of the executing command
        @rtype: tuple(L{paramiko.ChannelFile}, L{paramiko.ChannelFile},
                      L{paramiko.ChannelFile})

        @raise SSHException: if the server fails to execute the command
        """
        self.last_command = command
        return self.cli.exec_command(command, bufsize, get_pty=get_pty)

    def recv_exit_status(self, command, timeout=10, get_pty=False):
        """
        Execute a command and get its return value

        @param command: command to execute
        @type command: str

        @param timeout: command execution timeout
        @type timeout: int

        @param get_pty: get pty
        @type get_pty: bool

        @return: the exit code of the process or None in case of timeout
        @rtype: int or None
        """
        status = None
        self.last_command = command
        stdin, stdout, stderr = self.cli.exec_command(command, get_pty=get_pty)
        if stdout and stderr and stdin:
            for _ in xrange(timeout):
                if stdout.channel.exit_status_ready():
                    status = stdout.channel.recv_exit_status()
                    break
                time.sleep(1)

            self.last_stdout = stdout.read()
            self.last_stderr = stderr.read()

            stdin.close()
            stdout.close()
            stderr.close()
        return status

    def forward_tunnel(self, local_port, remote_host, remote_port):
        """
        Create forwarding tunnel (ssh -L)

        @param local_port: local port to bind (use 0 for autoselect)
        @type command: int

        @param remote_host: remote host
        @type command: str

        @param remote_port: remote port
        @type command: int

        @return: local port
        @rtype: int
        """
        class SubHandler(ForwardHandler):
            chain_host = remote_host
            chain_port = remote_port
            ssh_transport = self.cli.get_transport()
        fserver = ForwardServer(('', local_port), SubHandler)
        self.forwardthread = threading.Thread(target=_forward_threadfunc, args=(self, fserver))
        self.forwardthread.setDaemon(True)
        self.forwardthread.start()
        return fserver.server_address[1]


def _forward_threadfunc(connection, forwardserver):
    while hasattr(connection, '_lazy_cli'):
        # stop handling requests when cli was destroyed
        forwardserver.handle_request()


class ForwardServer(SocketServer.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class ForwardHandler(SocketServer.BaseRequestHandler):
# pylint: disable=E1101
    def __init__(self, *args, **kwargs):
        SocketServer.BaseRequestHandler.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger('valid.connection')

    def handle(self):
        self.logger = logging.getLogger('valid.connection')
        try:
            chan = self.ssh_transport.open_channel('direct-tcpip',
                                                   (self.chain_host, self.chain_port),
                                                   self.request.getpeername())
        except Exception, exc:
            self.logger.debug('Incoming request to %s:%d failed: %s', self.chain_host, self.chain_port, repr(exc))
            return
        if chan is None:
            self.logger.debug('Incoming request to %s:%d was rejected by the SSH server.', self.chain_host, self.chain_port)
            return

        peername = self.request.getpeername()

        self.logger.debug('Connected!  Tunnel open %r -> %r -> %r', peername, chan.getpeername(), (self.chain_host, self.chain_port))
        while True:
            rlist, _, _ = select.select([self.request, chan], [], [])
            if self.request in rlist:
                data = self.request.recv(1024)
                if len(data) == 0:
                    break
                chan.send(data)
            if chan in rlist:
                data = chan.recv(1024)
                if len(data) == 0:
                    break
                self.request.send(data)
        chan.close()
        self.request.close()
        self.logger.debug('Tunnel closed from %r', peername)


class ExpectFailed(AssertionError):
    '''
    Exception to represent expectation error
    '''
    pass


class Expect(object):
    '''
    Stateless class to do expect-ike stuff over connections
    '''
    @staticmethod
    def expect_list(connection, regexp_list, timeout=10):
        '''
        Expect a list of expressions

        @param connection: Connection to the host
        @type connection: L{Connection}

        @param regexp_list: regular expressions and associated return values
        @type regexp_list: list of (regexp, return value)

        @param timeout: timeout for performing expect operation
        @type timeout: int

        @return: propper return value from regexp_list
        @rtype: return value

        @raises ExpectFailed
        '''
        result = ""
        count = 0
        while count < timeout:
            try:
                recv_part = connection.channel.recv(16384)
                logging.getLogger('valid.expect').debug("RCV: " + recv_part)
                if connection.output_shell:
                    sys.stdout.write(recv_part)
                result += recv_part
            except socket.timeout:
                # socket.timeout here means 'no more data'
                pass

            for (regexp, retvalue) in regexp_list:
                # search for the first matching regexp and return desired value
                if re.match(regexp, result):
                    return retvalue
            time.sleep(1)
            count += 1
        raise ExpectFailed(result)

    @staticmethod
    def expect(connection, strexp, timeout=10):
        '''
        Expect one expression

        @param connection: Connection to the host
        @type connection: L{Connection}

        @param strexp: string to convert to expression (.*string.*)
        @type strexp: str

        @param timeout: timeout for performing expect operation
        @type timeout: int

        @return: True if succeeded
        @rtype: bool

        @raises ExpectFailed
        '''
        return Expect.expect_list(connection,
                                  [(re.compile(".*" + strexp + ".*",
                                               re.DOTALL), True)],
                                  timeout)

    @staticmethod
    def match(connection, regexp, grouplist=[1], timeout=10):
        '''
        Match against an expression

        @param connection: Connection to the host
        @type connection: L{Connection}

        @param regexp: compiled regular expression
        @type regexp: L{SRE_Pattern}

        @param grouplist: list of groups to return
        @type group: list of int

        @param timeout: timeout for performing expect operation
        @type timeout: int

        @return: matched string
        @rtype: str

        @raises ExpectFailed
        '''
        logging.getLogger('valid.expect').debug("MATCHING: " + regexp.pattern)
        result = ""
        count = 0
        while count < timeout:
            try:
                recv_part = connection.channel.recv(16384)
                logging.getLogger('valid.expect').debug("RCV: " + recv_part)
                if connection.output_shell:
                    sys.stdout.write(recv_part)
                result += recv_part
            except socket.timeout:
                # socket.timeout here means 'no more data'
                pass

            match = regexp.match(result)
            if match:
                ret_list = []
                for group in grouplist:
                    logging.getLogger('valid.expect').debug("matched: " + match.group(group))
                    ret_list.append(match.group(group))
                return ret_list
            time.sleep(1)
            count += 1
        raise ExpectFailed(result)

    @staticmethod
    def enter(connection, command):
        '''
        Enter a command to the channel (with '\n' appended)

        @param connection: Connection to the host
        @type connection: L{Connection}

        @param command: command to execute
        @type command: str

        @return: number of bytes actually sent
        @rtype: int
        '''
        return connection.channel.send(command + "\n")

    @staticmethod
    def ping_pong(connection, command, strexp, timeout=10):
        '''
        Enter a command and wait for something to happen (enter + expect
        combined)

        @param connection: connection to the host
        @type connection: L{Connection}

        @param command: command to execute
        @type command: str

        @param strexp: string to convert to expression (.*string.*)
        @type strexp: str

        @param timeout: timeout for performing expect operation
        @type  timeout: int

        @return: True if succeeded
        @rtype: bool

        @raises ExpectFailed
        '''
        Expect.enter(connection, command)
        return Expect.expect(connection, strexp, timeout)

    @staticmethod
    def expect_retval(connection, command, expected_status=0, timeout=10):
        '''
        Run command and expect specified return valud

        @param connection: connection to the host
        @type connection: L{Connection}

        @param command: command to execute
        @type command: str

        @param expected_status: expected return value
        @type expected_status: int

        @param timeout: timeout for performing expect operation
        @type  timeout: int

        @return: return value
        @rtype: int

        @raises ExpectFailed
        '''
        retval = connection.recv_exit_status(command, timeout)
        if retval is None:
            raise ExpectFailed("Got timeout (%i seconds) while executing '%s'"
                               % (timeout, command))
        elif retval != expected_status:
            raise ExpectFailed("Got %s exit status (%s expected)"
                               % (retval, expected_status))
        if connection.output_shell:
            sys.stdout.write("Run '%s', got %i return value\n"
                             % (command, retval))
        return retval


__all__ = ['ValidConnection', 'ValidConnectionException', 'Expect', 'ExpectFailed']
