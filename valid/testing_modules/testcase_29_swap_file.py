from valid.valid_testcase import *
import json

class testcase_29_swap_file(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, '[ ! -z "`curl http://169.254.169.254/latest/dynamic/instance-identity/signature`" ] && echo SUCCESS', "[^ ]SUCCESS")
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
            size = self.command(connection, "parted -l | grep linux-swap | awk '{print $4}' | awk -F'MB' '{print $1}'")
            partition = self.command(connection, "parted -l | grep -B 5 swap | grep ^Disk | awk '{print $2}' | sed '$s/.$//' | head -1")
            if size and partition:   
                self.ping_pong(connection, "[ %s -gt 0 ] && echo SUCCESS" % size, "\r\nSUCCESS\r\n")
                self.ping_pong(connection, "swapoff " + partition + "; echo SUCCESS" % size, "\r\nSUCCESS\r\n")
                self.ping_pong(connection, "swapon " + partition + "&& echo SUCCESS" % size, "\r\nSUCCESS\r\n")
                self.ping_pong(connection, "swapoff " + partition + " && swapon " + partition +  "&& echo SUCCESS" % size, "\r\nSUCCESS\r\n")
        return self.log
