from valid.valid_testcase import *


class testcase_33_userdata(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if params["userdata"]:
            if self.get_result(connection, "rpm -q --queryformat '%{NAME}\n' cloud-init", 5) == "cloud-init":
                testable = False
                if "touch  /userdata_test" in params["userdata"]:
                    testable = True
                    self.get_return_value(connection, "ls -l /userdata_test")
                if "yum install -y httpd" in params["userdata"]:
                    testable = True
                    self.get_return_value(connection, "rpm -q httpd")
                if not testable:
                    self.log.append({
                            "result": "skip",
                            "comment": "cannot test provided userdata"
                            })
            else:
                self.log.append({
                        "result": "skip",
                        "comment": "no cloud-init package"
                        })
        else:
            self.log.append({
                    "result": "skip",
                    "comment": "no userdata"
                    })
        return self.log
