from valid.valid_testcase import *


class testcase_32_ephemeral(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"].upper()
        has_ephemeral = False
        for bdev in params["bmap"]:
            if "ephemeral_name" in bdev.keys():
                name = bdev["name"]
                if (prod in ["RHEL", "BETA"]) and (ver.startswith("5.")):
                    if name.startswith("/dev/xvd"):
                        # no xvd* for RHEL5
                        continue
                else:
                    if name.startswith("/dev/sd"):
                        name = "/dev/xvd" + name[7:]
                    if params["virtualization"] != "hvm" and len(name) == 9 and ord(name[8]) < ord('w'):
                        # there is a 4-letter shift
                        name = name[:8] + chr(ord(name[8]) + 4)
                has_ephemeral = True
                self.get_return_value(connection, "fdisk -l %s | grep ^Disk" % name, 30)
                self.get_return_value(connection, "mkfs.vfat -I %s" % name, 60)
        if not has_ephemeral:
            self.log.append({
                    "result": "skip",
                    "comment": "no ephemeral devices in block map"
                    })
        return self.log
