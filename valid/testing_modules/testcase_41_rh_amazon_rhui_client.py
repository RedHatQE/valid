import paramiko
from valid.valid_testcase import *


class testcase_41_rh_amazon_rhui_client(ValidTestcase):
    """
    Check for rh-amazon-rhui-client
    """
    tags = ['default']
    stages = ['stage1']
    not_applicable = {'product': '(?i)FEDORA'}

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        if prod == 'RHEL':
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client')
        elif prod == 'BETA':
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-beta')
        elif prod == "RHS":
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-rhs')
        elif prod == "JPEAP" and ver.startswith("5."):
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-jbeap5')
        elif prod == "JPEAP" and ver.startswith("6."):
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-jbeap6')
        elif prod == "JBEWS" and ver.startswith("1."):
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-jbews1')
        elif prod == "JBEWS" and ver.startswith("2."):
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-jbews2')
        elif prod == "GRID":
            self.get_return_value(connection, 'rpm -q rh-amazon-rhui-client-mrg')
        else:
            self.log.append({'result': 'skip', 'comment': 'not applicable for this product/version'})

        return self.log
