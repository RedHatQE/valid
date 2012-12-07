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
