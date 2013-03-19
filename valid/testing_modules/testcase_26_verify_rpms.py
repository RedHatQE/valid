from valid.valid_testcase import *


class testcase_26_verify_rpms(ValidTestcase):
    """
    Do rpm -Va and compare the number of packages with modified files
    """
    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA", "version": "5.*|6.*"}
    tags = ["default"]

    def test(self, connection, params):
        ver = params["version"]
        if ver.startswith("6."):
            release_pkg = "redhat-release-server"
            rpmv_cmp = "4"
            if ver[:3] in ["6.4"]:
                rpmv_cmp = "5"
            if ver[:3] in ["6.1", "6.3"]:
                rpmv_cmp = "5"
            elif ver.startswith("6.2"):
                rpmv_cmp = "6"
        elif ver.startswith("5."):
            release_pkg = "redhat-release"
            rpmv_cmp = "2"
            if ver[:4] in ["5.10", "5.11"]:
                rpmv_cmp = "3"
            elif ver[:3] in ["5.8", "5.9"]:
                rpmv_cmp = "3"

        rpmv = self.get_result(connection, "rpm -Va --nomtime --nosize --nomd5 | sort -fu | wc -l", 90)
        rpmrel = self.get_result(connection, "rpm -q --queryformat '%{RELEASE}\n' " + release_pkg + " | cut -d. -f1,2")

        if rpmv:
            self.get_return_value(connection, "[ %s = %s ]" % (rpmv, rpmv_cmp))
            self.get_return_value(connection, "[ %s = %s ]" % (rpmrel, ver))
            packagers = self.get_result(connection, "rpm -qa --queryformat '%{PACKAGER}\n' | sort -u | grep -v 'Red Hat, Inc.'", 30)
        return self.log
