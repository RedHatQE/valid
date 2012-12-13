from valid.valid_testcase import *

class testcase_25_uname(ValidTestcase):
    stages = ["stage2"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        if prod in ["RHEL", "BETA"] and ver.startswith("5."):
            uname_r = self.get_result(connection, "uname -r | sed 's,\.el5xen,.el5,'")
            kernel_ver = self.get_result(connection, "rpm -q --queryformat '%{VERSION}-%{RELEASE}\n' kernel-xen | sort | tail -1")
        else:
            uname_r = self.get_result(connection, "uname -r")
            kernel_ver = self.get_result(connection, "rpm -q --queryformat '%{VERSION}-%{RELEASE}.%{ARCH}\n' kernel | sort | tail -1")
        uname_o = self.get_result(connection, "uname -o")
        if uname_r and uname_o and kernel_ver:
            self.get_return_value(connection, "[ %s = %s ]" % (kernel_ver, uname_r))
            self.get_return_value(connection, "[ %s = 'GNU/Linux' ]" % uname_o)
            self.get_return_value(connection, "grep UPDATEDEFAULT=yes /etc/sysconfig/kernel")
            self.get_return_value(connection, "grep DEFAULTKERNEL=kernel /etc/sysconfig/kernel")
        return self.log
