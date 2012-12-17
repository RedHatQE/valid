from valid.valid_testcase import *
import re


class testcase_08_memory(ValidTestcase):
    stages = ["stage1", "stage2"]

    def test(self, connection, params):
        if not params["hwp"]["memory"]:
            self.log.append({"result": "failure", "comment": "memory parameter in hwp is not set"})
        else:
            values = self.match(connection, "grep 'MemTotal:' /proc/meminfo", re.compile(".*\r\nMemTotal:\s*([0-9]+) ", re.DOTALL))
            if values:
                self.get_return_value(connection, "[ %s -gt %s ]" % (values[0], params["hwp"]["memory"]))
        return self.log
