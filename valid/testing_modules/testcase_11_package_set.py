import os
from valid.valid_testcase import *


class testcase_11_package_set(ValidTestcase):
    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA|FEDORA"}

    def test(self, connection, params):
        packages = self.match(connection, "rpm -qa --queryformat '%{NAME},' && echo", re.compile(".*\r\n(.*),\r\n.*", re.DOTALL), timeout=30)
        if packages:
            basepath = "/usr/share/valid/data/packages_"
            path = ""
            if params["product"].upper() == "FEDORA":
                basepath += "fedora_"
                if os.path.exists(basepath + params["version"]):
                    path = basepath + params["version"]
            else:
                basepath += "rhel_"
                if (len(params["version"]) > 2) and os.path.exists(basepath + params["version"][0] + params["version"][2]):
                    path = basepath + params["version"][0] + params["version"][2]
                elif (len(params["version"]) > 0) and os.path.exists(basepath + params["version"][0]):
                    path = basepath + params["version"][0]
            if path == "":
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
        return self.log
