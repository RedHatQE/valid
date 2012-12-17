from valid.valid_testcase import *


class testcase_27_yum_repos(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        repos = self.get_result(connection, "ls /etc/yum.repos.d/*.repo | wc -l")
        repos_redhat = self.get_result(connection, "ls /etc/yum.repos.d/redhat*.repo | wc -l")
        repos_rhel = self.get_result(connection, "ls /etc/yum.repos.d/rhel*.repo | wc -l")
        if prod == "BETA":
            repos_cmp = 4
            repos_redhat_cmp = 2
        elif prod == "RHEL":
            repos_cmp = 6
            repos_redhat_cmp = 4
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL only"})
            return self.log

        if prod in ["RHEL", "BETA"] and ver.startswith("6."):
            repos_rhel_cmp = 0
        elif prod in ["RHEL", "BETA"] and ver.startswith("5."):
            repos_rhel_cmp = 1
        else:
            self.log.append({"result": "failure", "comment": "this test is for RHEL5/RHEL6 only"})

        if repos and repos_rhel and repos_redhat:
            self.get_return_value(connection, "[ %s = %s ]" % (repos, repos_cmp))
            self.get_return_value(connection, "[ %s = %s ]" % (repos_redhat, repos_redhat_cmp))
            self.get_return_value(connection, "[ %s = %s ]" % (repos_rhel, repos_rhel_cmp))
        return self.log
