from valid.valid_testcase import *


class testcase_01_bash_history(ValidTestcase):
    """
    Ensure /root/.bash_history file is empty
    """
    stages = ["stage1"]
    tags = ["default"]

    def test(self, connection, params):
        self.ping_pong(connection, "[ ! -f ~/.bash_history ] && echo 0 || cat ~/.bash_history | wc -l", "\r\n0\r\n")
        return self.log
