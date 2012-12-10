from valid.valid_testcase import *
import re

class testcase_08_memory(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if not params["hwp"]["memory"]:
            self.log.append({"result": "failure", "comment": "memory parameter in hwp is not set"})
        else:
            values = self.match(connection, "grep 'MemTotal:' /proc/meminfo", re.compile(".*\r\nMemTotal:\s*([0-9]+) ", re.DOTALL))
            if values:
                self.ping_pong(connection, "[ %s -gt %s ] && echo SUCCESS" % (values[0], params["hwp"]["memory"]), "[^ ]SUCCESS")
        return self.log
