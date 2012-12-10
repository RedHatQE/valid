from valid.valid_testcase import *

class testcase_02_bash_history(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.ping_pong(connection, "[ ! -f ~/.bash_history ] && echo 0 || cat ~/.bash_history | wc -l", "\r\n0\r\n")
        return self.log
