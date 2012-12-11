from valid.valid_testcase import *
import json

class testcase_14_host_details(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        self.get_return_value(connection, '[ ! -z "`curl http://169.254.169.254/latest/dynamic/instance-identity/signature`" ]')
        json_str = self.match(connection, "curl http://169.254.169.254/latest/dynamic/instance-identity/document", re.compile(".*({.*}).*", re.DOTALL))
        if json_str:
            try:
                js = json.loads(json_str[0])
                self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["imageId"], params["ami"]))
                self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["architecture"], params["hwp"]["arch"]))
                self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["region"], params["region"]))
                if params["itype"] == "hourly":
                    self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["billingProducts"][0], "bp-6fa54006"))
                elif params["itype"] == "access":
                    self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["billingProducts"][0], "bp-63a5400a"))
            except KeyError:
                self.log.append({"result": "failure", "comment": "failed to check instance details, " + e.message})
        else:
            self.log.append({"result": "failure", "comment": "failed to get instance details"})
        return self.log
