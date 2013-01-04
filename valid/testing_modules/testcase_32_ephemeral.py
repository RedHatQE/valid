from valid.valid_testcase import *


class testcase_32_ephemeral(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        has_ephemeral = False
        for bdev in params["bmap"]:
            if "ephemeral_name" in bdev.keys():
                name = bdev["name"]
                if name.startswith("/dev/sd"):
                    name = "/dev/xvd" + name[7:]
                has_ephemeral = True
                self.get_return_value(connection, "fdisk -l %s | grep ^Disk" % name, 30)
                self.get_return_value(connection, "mkfs.vfat %s" % name, 60)
        if not has_ephemeral:
            self.log.append({
                    "result": "skip",
                    "comment": "no ephemeral devices in block map"
                    })
        return self.log
