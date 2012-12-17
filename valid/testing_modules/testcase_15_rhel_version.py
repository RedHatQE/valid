from valid.valid_testcase import *


class testcase_15_rhel_version(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA"):
            rhelv = self.match(connection, "rpm -q --qf '%{RELEASE}\n' --whatprovides redhat-release", re.compile(".*\r\n([0-9]\.[0-9]\..*)\r\n.*", re.DOTALL))
            if rhelv:
                self.get_return_value(connection, "[ '%s' = '%s' ]" % (params["version"], rhelv[0][:len(params["version"])]))
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL only"})
        return self.log
