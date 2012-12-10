from valid.valid_testcase import *

class testcase_09_nameserver(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
    	self.ping_pong(connection, "dig clock.redhat.com | grep 66.187.233.4 && echo SUCCESS", "[^ ]SUCCESS")
        return self.log
