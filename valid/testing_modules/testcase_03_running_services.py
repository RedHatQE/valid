from valid.valid_testcase import *

import yaml


class testcase_03_running_services(ValidTestcase):
    """
    Check for running services
    """
    stages = ['stage1']
    tags = ['default']
    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        with open(self.datadir + '/running_services.yaml') as expected_services_fd:
            all_services = yaml.safe_load(expected_services_fd)
        try:
            expected_services = all_services['%s_%s' % (prod, ver)]
        except KeyError as e:
            self.log.append({
                'result': 'skip',
                'comment': 'unsupported region and/or product-version combination'})
            return self.log

        is_systemd = self.get_result(connection, 'rpm -q systemd > /dev/null && echo True || echo False')
        if is_systemd == 'True':
            for service in expected_services:
                self.get_return_value(connection, 'systemctl is-active %s.service' % service)
        else:
            for service in expected_services:
                self.ping_pong(connection, 'chkconfig --list %s' % service, '3:on')
        return self.log
