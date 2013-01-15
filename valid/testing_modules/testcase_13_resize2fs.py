from valid.valid_testcase import *


class testcase_13_resize2fs(ValidTestcase):
    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA", "version": "5.*|6.*", "virtualization": "(?!hvm)"}

    def test(self, connection, params):
        """The instances are always created with a 15GB root device (unlike
        the AWS default of 8GB. The point is whether we're able to allocate
        the space. Please note that cloud-init does the resize automatically.
        """
        if self.get_return_value(connection, 'rpm -q cloud-init', nolog=True) == 1:
            # cloud-init not installed, resize
            if (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("6."):
                self.get_return_value(connection, "if [ -b /dev/xvde1 ]; then resize2fs -p /dev/xvde1 15000M ; else resize2fs -p /dev/xvda1 15000M; fi", 90)
            elif (params["product"].upper() == "RHEL" or params["product"].upper() == "BETA") and params["version"].startswith("5."):
                self.get_return_value(connection, "resize2fs -p /dev/sda1 15000M", 90)
        self.get_return_value(connection, "df -h | grep 15G")
        return self.log
