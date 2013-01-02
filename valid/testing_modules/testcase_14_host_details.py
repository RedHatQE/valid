from valid.valid_testcase import *
import json


class testcase_14_host_details(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        self.get_return_value(connection, '[ ! -z "`curl http://169.254.169.254/latest/dynamic/instance-identity/signature`" ]')
        json_str = self.match(connection, "curl http://169.254.169.254/latest/dynamic/instance-identity/document", re.compile(".*({.*}).*", re.DOTALL))
        if json_str:
            try:
                js = json.loads(json_str[0])
                if "billingProducts" in js.keys() and js["billingProducts"] != None:
                    billingProduct = js["billingProducts"][0]
                else:
                    billingProduct = ""
                self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["imageId"], params["ami"]))
                self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["architecture"], params["arch"]))
                self.get_return_value(connection, '[ "%s" = "%s" ]' % (js["region"], params["region"]))
                if prod in ["RHEL", "BETA"]:
                    if params["itype"] == "hourly":
                        self.get_return_value(connection, '[ "%s" = "%s" ]' % (billingProduct, "bp-6fa54006"))
                    elif params["itype"] == "access":
                        self.get_return_value(connection, '[ "%s" = "%s" ]' % (billingProduct, "bp-63a5400a"))
            except KeyError:
                self.log.append({"result": "failure", "comment": "failed to check instance details, " + e.message})
        else:
            self.log.append({"result": "failure", "comment": "failed to get instance details"})
        return self.log
