from valid.valid_testcase import *
import json

class testcase_29_swap_file(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, '[ ! -z "`curl http://169.254.169.254/latest/dynamic/instance-identity/signature`" ]')
        json_str = self.match(connection, "curl http://169.254.169.254/latest/dynamic/instance-identity/document", re.compile(".*({.*}).*", re.DOTALL))
        has_swap = True
        if json_str:
            try:
                js = json.loads(json_str[0])
                if js["instanceType"] == "t1.micro":
                    has_swap = False
            except KeyError:
                self.log.append({"result": "failure", "comment": "failed to check instance type, " + e.message})
                return self.log
        else:
            self.log.append({"result": "failure", "comment": "failed to get instance details"})
            return self.log
        if has_swap:
            size = self.get_result(connection, "parted -l | grep linux-swap | awk '{print $4}' | awk -F'MB' '{print $1}'", 15)
            partition = self.get_result(connection, "parted -l | grep -B 5 swap | grep ^Disk | awk '{print $2}' | sed '$s/.$//' | head -1", 15)
            if size and partition:
                self.get_return_value(connection, "[ " + size + " -gt 0 ]")
                self.get_return_value(connection, "swapoff " + partition + " ; echo")
                self.get_return_value(connection, "swapon " + partition, 30)
                self.get_return_value(connection, "swapoff " + partition + " && swapon " + partition, 30)
        return self.log
