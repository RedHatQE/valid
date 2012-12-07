from valid.valid_testcase import *
import json

class testcase_14_host_details(ValidTestcase):
    def test(self, connection, params):
        self.ping_pong(connection, '[ ! -z "`curl http://169.254.169.254/latest/dynamic/instance-identity/signature`" ] && echo SUCCESS', "[^ ]SUCCESS")
        json_str = self.match(connection, "curl http://169.254.169.254/latest/dynamic/instance-identity/document", re.compile(".*({.*}).*", re.DOTALL))
        if json_str:
            try:
                js = json.loads(json_str[0])
                self.ping_pong(connection, '[ "%s" = "%s" ] && echo SUCCESS' % (js["imageId"], params["ami"]), "[^ ]SUCCESS")
                self.ping_pong(connection, '[ "%s" = "%s" ] && echo SUCCESS' % (js["architecture"], params["hwp"]["arch"]), "[^ ]SUCCESS")
                self.ping_pong(connection, '[ "%s" = "%s" ] && echo SUCCESS' % (js["region"], params["region"]), "[^ ]SUCCESS")
                if params["itype"] == "hourly":
                    self.ping_pong(connection, '[ "%s" = "%s" ] && echo SUCCESS' % (js["billingProducts"][0], "bp-6fa54006"), "[^ ]SUCCESS")
                elif params["itype"] == "access":
                    self.ping_pong(connection, '[ "%s" = "%s" ] && echo SUCCESS' % (js["billingProducts"][0], "bp-63a5400a"), "[^ ]SUCCESS")
            except KeyError:
                self.log.append({"result": "failure", "comment": "failed to check instance details, " + e.message})
        else:
            self.log.append({"result": "failure", "comment": "failed to get instance details"})
        return self.log
