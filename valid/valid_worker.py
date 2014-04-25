import paramiko
import multiprocessing
import random
import logging
import time
import os
import tempfile
import sys
import socket
import traceback
import threading

from valid import valid_connection
from valid import cloud

class WorkerProcess(multiprocessing.Process):
    """
    Worker Process to do actual testing
    """
    def __init__(self, shareddata):
        """
        Create WorkerProcess object
        """
        multiprocessing.Process.__init__(self, name='WorkerProcess_%s' % random.randint(1, 16384), target=self.runner, args=(shareddata,))
        self.connection_cache = {}
        self.logger = logging.getLogger('valid.runner')
        if shareddata.debug:
            logging.getLogger('paramiko').setLevel(logging.DEBUG)
        else:
            logging.getLogger('paramiko').setLevel(logging.ERROR)

    def runner(self, shareddata):
        """
        Run process:
        - Get tasks from mainq (create/setup/test/terminate)
        - Check for maxtries
        """
        self.shareddata = shareddata
        while True:
            self.logger.debug(self.name + ': heartbeat numprocesses: %i' % shareddata.numprocesses.value)
            self.logger.debug(self.name + ': heartbeat numthreads: %i' % len(threading.enumerate()))
            if shareddata.resultdic.keys() == [] and shareddata.time2die.get():
                self.logger.debug(self.name + ': nothing to do and time to die, suiciding')
                shareddata.numprocesses.value -= 1
                break
            if shareddata.mainq.empty():
                if shareddata.numprocesses.value > shareddata.minprocesses:
                    self.logger.debug(self.name + ': too many worker processes and nothing to do, suiciding')
                    shareddata.numprocesses.value -= 1
                    break
                time.sleep(random.randint(2, 10))
                continue
            try:
                (ntry, action, params) = shareddata.mainq.get()
            except:
                continue
            if ntry > shareddata.maxtries:
                # Maxtries reached: something is wrong, reporting 'failure' and terminating the instance
                self.logger.error(self.name + ': ' + action + ':' + str(params) + ' failed after ' + str(shareddata.maxtries) + ' tries')
                if action in ['create', 'setup']:
                    params['result'] = {action: 'failure'}
                elif action == 'test':
                    params['result'] = {params['stages'][0]: 'failure'}
                if action != 'terminate':
                    self.abort_testing(params)
                continue
            if action == 'create':
                # create an instance
                self.logger.debug(self.name + ': picking up ' + params['iname'])
                self.do_create(ntry, params)
            elif action == 'setup':
                # setup instance for testing
                self.logger.debug(self.name + ': doing setup for ' + params['iname'])
                self.do_setup(ntry, params)
            elif action == 'test':
                # do some testing
                self.logger.debug(self.name + ': doing testing for ' + params['iname'])
                self.do_testing(ntry, params)
            elif action == 'terminate':
                # terminate instance
                self.logger.debug(self.name + ': terminating ' + params['iname'])
                self.do_terminate(ntry, params)

    def abort_testing(self, params):
        """
        Something went wrong and we need to abort testing

        @param params: list of testing parameters
        @type params: list
        """
        # we need to change expected value in resultdic
        with self.shareddata.resultdic_lock:
            transd = self.shareddata.resultdic[params['transaction_id']]
            transd[params['ami']]['ninstances'] -= (len(params['stages']) - 1)
            self.shareddata.resultdic[params['transaction_id']] = transd
        self.report_results(params)
        if 'id' in params.keys():
            # Try to terminate the instance
            self.shareddata.mainq.put((0, 'terminate', params.copy()))

    def report_results(self, params):
        """
        Report results

        @param params: list of testing parameters
        @type params: list
        """
        console_output = ''
        if len(params['stages']) == 1:
            try:
                driver = cloud.get_driver(params['cloud'], self.logger, self.shareddata.maxwait)
                #getting console output after last stage
                console_output = driver.get_console_output(params)
                self.logger.debug(self.name + ': got console output for %s: %s' % (params['iname'], console_output))
            except Exception, err:
                self.logger.error(self.name + ': report_results: Failed to get console output %s' % err)
        report_value = {'instance_type': params['cloudhwname'],
                        'ami': params['ami'],
                        'region': params['region'],
                        'arch': params['arch'],
                        'version': params['version'],
                        'product': params['product'],
                        'console_output': console_output,
                        'result': params['result']}
        self.logger.debug(self.name + ': reporting result: %s' % (report_value, ))
        self.logger.debug(self.name + ': self.resultdic before report: %s' % (self.shareddata.resultdic.items(), ))
        with self.shareddata.resultdic_lock:
            transd = self.shareddata.resultdic[params['transaction_id']]
            transd[params['ami']]['instances'].append(report_value)
            self.shareddata.resultdic[params['transaction_id']] = transd
        self.logger.debug(self.name + ': self.resultdic after report: %s' % (self.shareddata.resultdic.items(), ))

    def do_create(self, ntry, params):
        """
        Create stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        self.logger.debug(self.name + ': trying to create instance  ' + params['iname'] + ', ntry ' + str(ntry))
        driver = cloud.get_driver(params['cloud'], self.logger, self.shareddata.maxwait)
        try:
            params_new = driver.create(params)
            self.shareddata.mainq.put((0, 'setup', params_new.copy()))
        except cloud.base.TemporaryCloudException, exc:
            self.logger.debug('%s: Temporary Cloud Exception: %s', self.name, exc)
            time.sleep(10)
            self.shareddata.mainq.put((ntry, 'create', params.copy()))
        except cloud.base.PermanentCloudException, exc:
            self.logger.error('%s: Permanent Cloud Exception: %s', self.name, exc)
            params['result'] = {'create': str(exc)}
            self.abort_testing(params)
        except cloud.base.SkipCloudException, exc:
            self.logger.debug('%s: Skip Cloud Exception: %s', self.name, exc)
            params['result'] = {'create': 'skip'}
            self.abort_testing(params)
        except cloud.base.UnknownCloudException, exc:
            self.logger.error('%s: Unknown Cloud Exception: %s', self.name, exc)
            time.sleep(10)
            self.shareddata.mainq.put((ntry, 'create', params.copy()))
            ntry += 1

    def do_setup(self, ntry, params):
        """
        Setup stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        try:
            self.logger.debug(self.name + ': trying to do setup for ' + params['iname'] + ', ntry ' + str(ntry))
            ssh_key = params['ssh']['keyfile']
            self.logger.debug(self.name + ': ssh-key ' + ssh_key)

            for user in ['ec2-user', 'fedora']:
                # If we're able to login with one of these users allow root ssh immediately
                try:
                    con = self.get_connection(params['hostname'], user, ssh_key)
                    valid_connection.Expect.ping_pong(con, 'uname', 'Linux')
                    valid_connection.Expect.ping_pong(con, 'sudo su -c \'cp -af /home/' + user + '/.ssh/authorized_keys /root/.ssh/authorized_keys; chown root.root /root/.ssh/authorized_keys; restorecon /root/.ssh/authorized_keys\' && echo SUCCESS', '\r\nSUCCESS\r\n')
                    self.close_connection(params['hostname'], user, ssh_key)
                except:
                    pass

            con = self.get_connection(params['hostname'], 'root', ssh_key)
            valid_connection.Expect.ping_pong(con, 'uname', 'Linux')

            self.logger.debug(self.name + ': sleeping for ' + str(self.shareddata.settlewait) + ' sec. to make sure instance has been settled.')
            time.sleep(self.shareddata.settlewait)

            setup_scripts = []
            if self.shareddata.global_setup_script is not None:
                # upload and execute a setup script as root in /tmp/
                self.logger.debug(self.name + ': executing global setup script: %s' % self.shareddata.global_setup_script)
                local_script_path = os.path.expandvars(os.path.expanduser(self.shareddata.global_setup_script))
                setup_scripts.append(local_script_path)
            tfile = tempfile.NamedTemporaryFile(delete=False)
            if 'setup' in params.keys() and params['setup']:
                if type(params['setup']) is list:
                    params['setup'] = '\n'.join([str(x) for x in params['setup']])
                self.logger.debug(self.name + ': executing ami-specific setup script: %s' % params['setup'])
                tfile.write(params['setup'])
                setup_scripts.append(tfile.name)
            tfile.close()
            for script in setup_scripts:
                remote_script_path = '/tmp/' + os.path.basename(script)
                con.sftp.put(script, remote_script_path)
                con.sftp.chmod(remote_script_path, 0700)
                self.remote_command(con, remote_script_path)
            os.unlink(tfile.name)
            self.shareddata.mainq.put((0, 'test', params.copy()))
        except (socket.error, paramiko.SFTPError, paramiko.SSHException, paramiko.PasswordRequiredException, paramiko.AuthenticationException, valid_connection.ExpectFailed) as err:
            self.logger.debug(self.name + ': got \'predictable\' error during instance setup, %s, ntry: %i' % (err, ntry))
            self.logger.debug(self.name + ':' + traceback.format_exc())
            time.sleep(10)
            self.shareddata.mainq.put((ntry + 1, 'setup', params.copy()))
        except Exception, err:
            self.logger.error(self.name + ': got error during instance setup, %s %s, ntry: %i' % (type(err), err, ntry))
            self.logger.debug(self.name + ':' + traceback.format_exc())
            time.sleep(10)
            self.shareddata.mainq.put((ntry + 1, 'setup', params.copy()))

    def do_testing(self, ntry, params):
        """
        Testing stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        try:
            stage = params['stages'][0]
            self.logger.debug(self.name + ': trying to do testing for ' + params['iname'] + ' ' + stage + ', ntry ' + str(ntry))

            ssh_key = params['ssh']['keyfile']
            self.logger.debug(self.name + ': ssh-key ' + ssh_key)

            con = self.get_connection(params['hostname'], 'root', ssh_key)

            self.logger.info(self.name + ': doing testing for ' + params['iname'] + ' ' + stage)

            try:
                test_name = stage.split(':')[1]
                testcase = getattr(sys.modules['valid.testing_modules.' + test_name], test_name)()
                self.logger.debug(self.name + ': doing test ' + test_name + ' for ' + params['iname'] + ' ' + stage)
                test_result = testcase.test(con, params)
                self.logger.debug(self.name + ': ' + params['iname'] + ': test ' + test_name + ' finised with ' + str(test_result))
                result = test_result
            except (AttributeError, TypeError, NameError, IndexError, ValueError, KeyError), err:
                self.logger.error(self.name + ': bad test, %s %s' % (stage, err))
                self.logger.debug(self.name + ':' + traceback.format_exc())
                result = 'Failure'
            except (cloud.PermanentCloudException), err:
                self.logger.error(self.name + ': permanent cloud exception, %s %s' % (stage, err))
                self.logger.debug(self.name + ':' + traceback.format_exc())
                result = 'Failure'

            self.logger.info(self.name + ': done testing for ' + params['iname'] + ' ' + stage)

            params_new = params.copy()
            if len(params['stages']) > 1:
                params_new['stages'] = params['stages'][1:]
                self.shareddata.mainq.put((0, 'test', params_new))
            else:
                self.shareddata.mainq.put((0, 'terminate', params_new))
            self.logger.debug(self.name + ': done testing for ' + params['iname'] + ', result: ' + str(result))
            params['result'] = {params['stages'][0]: result}
            self.report_results(params)
        except (socket.error,
                paramiko.SFTPError,
                paramiko.SSHException,
                paramiko.PasswordRequiredException,
                paramiko.AuthenticationException,
                valid_connection.ExpectFailed) as err:
            # Looks like we've failed to connect to the instance
            self.logger.debug(self.name + ': got \'predictable\' error during instance testing, %s, ntry: %i' % (err, ntry))
            self.logger.debug(self.name + ':' + traceback.format_exc())
            time.sleep(10)
            self.shareddata.mainq.put((ntry + 1, 'test', params.copy()))
        except Exception, err:
            # Got unexpected error
            self.logger.error(self.name + ': got error during instance testing, %s %s, ntry: %i' % (type(err), err, ntry))
            self.logger.debug(self.name + ':' + traceback.format_exc())
            time.sleep(10)
            self.shareddata.mainq.put((ntry + 1, 'test', params.copy()))

    def do_terminate(self, ntry, params):
        """
        Terminate stage of testing

        @param ntry: number of try
        @type ntry: int

        @param params: list of testing parameters
        @type params: list
        """
        if 'keepalive' in params and params['keepalive'] is not None:
            self.logger.info(self.name + ': will not terminate %s (keepalive requested)' % params['iname'])
            return
        driver = cloud.get_driver(params['cloud'], self.logger, self.shareddata.maxwait)
        try:
            self.logger.debug(self.name + ': trying to terminata instance  ' + params['iname'] + ', ntry ' + str(ntry))
            driver.terminate(params)
            self.logger.info(self.name + ': terminated ' + params['iname'])
        except cloud.PermanentCloudException, err:
            self.logger.error(self.name + ': got permanent error during instance termination, %s %s' % (type(err), err))
        except cloud.TemporaryCloudException, err:
            self.logger.debug(self.name + ': got temporary error during instance termination, %s %s' % (type(err), err))
            self.shareddata.mainq.put((ntry, 'terminate', params.copy()))
        except Exception, err:
            self.logger.error(self.name + ': got error during instance termination, %s %s' % (type(err), err))
            self.logger.debug(self.name + ':' + traceback.format_exc())
            self.shareddata.mainq.put((ntry + 1, 'terminate', params.copy()))
        try:
            ssh_key = params['ssh']['keyfile']
            self.close_connection(params['hostname'], "root", ssh_key)
        except Exception, err:
            pass

    @staticmethod
    def remote_command(connection, command, timeout=5):
        """
        Execute a remote command via connection

        @param connection: Connection to the host
        @type connection: L{Connection}

        @param command: command to execute
        @type command: str

        @param timeout: timeout for performing expect operation
        @type  timeout: int

        @return: return value or None
        @rtype: int or None

        @raises valid_connection.ExpectFailed
        """
        status = connection.recv_exit_status(command + ' >/dev/null 2>&1', timeout)
        if status != 0:
            raise valid_connection.ExpectFailed('Command ' + command + ' failed with ' + str(status) + ' status.')
        return status

    def get_connection(self, hostname, user, ssh_key):
        """ Get connection """
        self.logger.debug(self.name + ': connection cache is: %s' % self.connection_cache)
        ikey = hostname + ":" + user + ":" + ssh_key
        self.logger.debug(self.name + ': searching for %s in connection cache' % ikey)
        con = None
        if ikey in self.connection_cache:
            con = self.connection_cache[ikey]
            self.logger.debug(self.name + ': found %s in connection cache (%s)' % (ikey, con))
        if con is not None:
            try:
                valid_connection.Expect.ping_pong(con, 'uname', 'Linux')
            except:
                # connection looks dead
                self.logger.debug(self.name + ': eliminating dead connection to %s' % ikey)
                con.disconnect()
                self.connection_cache.pop(ikey)
                con = None
        if con is None:
            self.logger.debug(self.name + ': creating connection to %s' % ikey)
            con = valid_connection.ValidConnection(hostname, user, ssh_key)
            self.logger.debug(self.name + ': created connection to %s (%s)' % (ikey, con))
            self.connection_cache[ikey] = con
        return con

    def close_connection(self, hostname, user, ssh_key):
        """ Close connection """
        ikey = hostname + ":" + user + ":" + ssh_key
        con = None
        if ikey in self.connection_cache:
            self.logger.debug(self.name + ': closing connection to %s' % ikey)
            con = self.connection_cache[ikey]
            self.connection_cache.pop(ikey)
        if con is not None:
            con.disconnect()
