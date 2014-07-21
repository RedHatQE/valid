""" Base test class """
import re
import logging
import multiprocessing
from registry import ValidTestcaseMetaClass
from valid.valid_connection import Expect, ExpectFailed


class ValidTestcase(object):
    """ Base test class """
    __metaclass__ = ValidTestcaseMetaClass

    datadir = '/usr/share/valid/data'

    def __init__(self):
        self.log = []
        self.logger = logging.getLogger('valid.testcase')

    def ping_pong(self, connection, command, expectation, timeout=10):
        """ Expect.ping_pong wrapper """
        self.logger.debug(multiprocessing.current_process().name + ": ping_pong '%s' expecting '%s'" % (command, expectation))
        result = {"command": command, "expectation": expectation}
        try:
            Expect.ping_pong(connection, command, expectation, timeout)
            result["result"] = "passed"
            self.logger.debug(multiprocessing.current_process().name + ": ping_pong passed")
        except ExpectFailed, err:
            result["result"] = "failed"
            result["actual"] = err.message
            self.logger.debug(multiprocessing.current_process().name + ": ping_pong failed: '%s'" % err.message)
        self.log.append(result)
        return result["result"]

    # pylint: disable=W0102
    def match(self, connection, command, regexp, grouplist=[1], timeout=10):
        """ Expect.match wrapper """
        try:
            self.logger.debug(multiprocessing.current_process().name + ": matching '%s' against '%s'" % (command, regexp.pattern))
            Expect.enter(connection, command)
            result = Expect.match(connection, regexp, grouplist, timeout)
            self.log.append({"result": "passed", "match": regexp.pattern, "command": command, "value": str(result)})
            self.logger.debug(multiprocessing.current_process().name + ": matched '%s'" % result)
            return result
        except ExpectFailed, err:
            self.log.append({"result": "failed", "match": regexp.pattern, "command": command, "actual": err.message})
            self.logger.debug(multiprocessing.current_process().name + ": match failed '%s'" % err.message)
            return None

    def get_result(self, connection, command, timeout=10):
        """ Expect.match wrapper """
        try:
            self.logger.debug(multiprocessing.current_process().name + ": getting result for '%s'" % command)
            Expect.enter(connection, "echo '###START###'; " + command + "; echo '###END###'")
            regexp = re.compile(".*\r\n###START###\r\n(.*)\r\n###END###\r\n.*", re.DOTALL)
            result = Expect.match(connection, regexp, [1], timeout)
            self.log.append({"result": "passed", "command": command, "value": result[0]})
            self.logger.debug(multiprocessing.current_process().name + ": got result: '%s'" % result[0])
            return result[0]
        except ExpectFailed, err:
            self.log.append({"result": "failed", "command": command, "actual": err.message})
            self.logger.debug(multiprocessing.current_process().name + ": getting failed: '%s'" % err.message)
            return None

    def get_return_value(self, connection, command, timeout=15, expected_status=0, nolog=False):
        """ Connection.recv_exit_status wrapper """
        self.logger.debug(multiprocessing.current_process().name + ": getting return value '%s'" % command)
        status = connection.recv_exit_status(command + " >/dev/null 2>&1", timeout)
        if not nolog:
            if status == expected_status:
                self.log.append({"result": "passed", "command": command})
            else:
                self.log.append({"result": "failed", "command": command, "actual": str(status)})
        self.logger.debug(multiprocessing.current_process().name + ": got '%s' status" % status)
        return status
