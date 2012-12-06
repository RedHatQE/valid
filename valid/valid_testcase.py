from patchwork.expect import *

class ValidTestcase(object):
    def __init__(self):
        self.log = []

    def ping_pong(self, connection, command, expectation):
        result = {"command": command, "expectation": expectation}
        try:
            Expect.ping_pong(connection, command, expectation)
            result["result"] = "passed"
        except ExpectFailed, e:
            result["result"] = "failed"
            result["actual"] = e.message
        self.log.append(result)
