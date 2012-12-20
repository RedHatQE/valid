import os
from valid.valid_testcase import *


class testcase_11_package_set(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA"):
            packages = self.match(connection, "rpm -qa --queryformat '%{NAME},' && echo", re.compile(".*\r\n(.*),\r\n.*", re.DOTALL), timeput=30)
            if packages:
                basepath = "/usr/share/valid/data/packages_rhel_"
                if (len(params["version"]) > 2) and os.path.exists(basepath + params["version"][0] + params["version"][2]):
                    path = basepath + params["version"][0] + params["version"][2]
                elif (len(params["version"]) > 0) and os.path.exists(basepath + params["version"][0]):
                    path = basepath + params["version"][0]
                else:
                    self.log.append({"result": "failure", "comment": "no package set for this os version"})
                    return self.log
                fd = open(path, "r")
                package_set_requred = set(fd.read().split('\n')[:-1])
                fd.close()
                package_set_got = set(packages[0].split(','))
                difference = package_set_requred.difference(package_set_got)
                if params["product"].upper() == "BETA" and len(difference) > 1:
                    self.log.append({"result": "failed", "comment": "Beta may lack not more than 1 package: " + str(difference)})
                elif params["product"].upper() == "RHEL" and len(difference) > 0:
                    self.log.append({"result": "failed", "comment": "RHEL must not lack packages: " + str(difference)})
                else:
                    self.log.append({"result": "passed", "comment": "All required package are included"})
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})
        return self.log
