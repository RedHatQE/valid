from valid.valid_testcase import *


class testcase_29_swap_file(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if params["hwp"]["name"] != "t1.micro" and params["hwp"]["virtualization"] != "hvm":
            size = self.get_result(connection, "parted -l | grep linux-swap | awk '{print $4}' | awk -F'MB' '{print $1}'", 15)
            partition = self.get_result(connection, "parted -l | grep -B 5 swap | grep ^Disk | awk '{print $2}' | sed '$s/.$//' | head -1", 15)
            if size and partition:
                self.get_return_value(connection, "[ " + size + " -gt 0 ]")
                self.get_return_value(connection, "swapoff " + partition + " ; echo")
                self.get_return_value(connection, "swapon " + partition, 30)
                self.get_return_value(connection, "swapoff " + partition + " && swapon " + partition, 30)
        else:
            self.log.append({"result": "passed", "comment": "no swap for this instance type"})
        return self.log
