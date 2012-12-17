import re
import logging
from patchwork.expect import *


class ValidTestcase(object):
    def __init__(self):
        self.log = []

    def ping_pong(self, connection, command, expectation, timeout=5):
        result = {"command": command, "expectation": expectation}
        try:
            Expect.ping_pong(connection, command, expectation, timeout)
            result["result"] = "passed"
        except ExpectFailed, e:
            result["result"] = "failed"
            result["actual"] = e.message
        self.log.append(result)

    def match(self, connection, command, regexp, grouplist=[1], timeout=5):
        try:
            Expect.enter(connection, command)
            result = Expect.match(connection, regexp, grouplist, timeout)
            self.log.append({"result": "passed", "match": regexp.pattern, "command": command, "value": str(result)})
            return result
        except ExpectFailed, e:
            self.log.append({"result": "failed", "match": regexp.pattern, "command": command, "actual": e.message})
            return None

    def get_result(self, connection, command, timeout=5):
        try:
            Expect.enter(connection, "echo '###START###'; " + command + "; echo '###END###'")
            regexp = re.compile(".*\r\n###START###\r\n(.*)\r\n###END###\r\n.*", re.DOTALL)
            result = Expect.match(connection, regexp, [1], timeout)
            self.log.append({"result": "passed", "command": command, "value": result[0]})
            return result[0]
        except ExpectFailed, e:
            self.log.append({"result": "failed", "command": command, "actual": e.message})
            return None

    def get_return_value(self, connection, command, timeout=5, expected_status=0):
        status = connection.recv_exit_status(command + " >/dev/null 2>&1", timeout)
        if status == expected_status:
            self.log.append({"result": "passed", "command": command})
        else:
            self.log.append({"result": "failed", "command": command, "actual": str(status)})
        return status
