""" This module contains testcase_61_yum_proxy test """
from valid.valid_testcase import ValidTestcase
import StringIO
import ConfigParser


class testcase_61_yum_proxy(ValidTestcase):
    """
    Try to use yum with proxy
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """
        yum_timeout = 300

        try:
            proxy = params['proxy']
            if params['version'].startswith('5'):
                yum_test_command = 'yum --disableplugin=fastestmirror repolist'
            else:
                yum_test_command = 'yum repolist'
        except KeyError:
            self.log.append({'result': 'skip', 'comment': 'No proxy set'})
            return self.log
        # update rh-amazon-rhui-client
        # the repo id is: rhui-<region>-client-config-server-<major version nr>
        self.get_return_value(
            connection,
            'yum --disablerepo=* --enablerepo=' +
            'rhui-%s-client-config-server-%s' % (params['region'], params['version'].split('.')[0]) + ' --nogpgcheck update -y',
            timeout=yum_timeout
        )

        # prepare the firewall blocking
        balancers = self.get_result(
            connection,
            'cat /etc/yum.repos.d/rhui-load-balancers.conf'
        ).split()
        for cds in balancers:
            # disable the cdses in firewall
            self.get_return_value(
                connection,
                'iptables -I OUTPUT -d %s -j DROP' % cds
            )
        # read the yum.conf
        # and provide the proxy setup
        try:
            yum_conf_fp = connection.sftp.open('/etc/yum.conf')
            yum_conf_data = yum_conf_fp.read()
            yum_conf_fp.close()
        except IOError, err:
            self.log.append({'result': 'failure',
                             'comment': 'failed to get actual repo list %s' % err
                             })
            return self.log
        # read as INI
        yum_conf_fp = StringIO.StringIO(yum_conf_data)
        yum_conf = ConfigParser.ConfigParser()
        import copy
        yum_conf_data_old = copy.deepcopy(yum_conf_data)
        try:
            yum_conf.readfp(yum_conf_fp)
        except ConfigParser.Error as err:
            self.log.append({
                'result': 'failure',
                'comment': 'failed parsing yum.conf: %s' % err
            })
            return self.log
        # provide the proxy config details
        if 'port' in proxy:
            yum_conf.set('main', 'proxy', 'https://' + proxy['host'] +
                         ':' + str(proxy['port']))
        else:
            yum_conf.set('main', 'proxy', 'https://' + proxy['host'])
        if 'user' in proxy:
            yum_conf.set('main', 'proxy_username', proxy['user'])
        if 'password' in proxy:
            yum_conf.set('main', 'proxy_password', proxy['password'])
        # write the data back
        try:
            yum_conf_fp = connection.sftp.open('/etc/yum.conf', 'w+')
            yum_conf.write(yum_conf_fp)
            yum_conf_fp.close()
        except IOError as err:
            self.log.append({
                'result': 'failure',
                'comment': 'couldn\'t write \'/etc/yum.conf\': %s' % err
            })
            return self.log
        # test all works
        self.get_result(
            connection,
            'yum clean all; ' + yum_test_command,
            timeout=yum_timeout
        )
        # restore original yum conf
        try:
            yum_conf_fp = connection.sftp.open('/etc/yum.conf', 'w+')
            yum_conf_fp.write(yum_conf_data_old)
            yum_conf_fp.close()
        except IOError as err:
            self.log.append({
                'result': 'failure',
                'comment': 'couldn\'t write \'/etc/yum.conf\': %s' % err
            })
            return self.log
        # try the same with an env variable
        if 'port' in proxy:
            https_proxy = proxy['host'] + ':' + str(proxy['port'])
        if 'user' in proxy and 'password' in proxy:
            https_proxy = 'https://' + proxy['user'] + ':' + proxy['password'] +\
                '@' + https_proxy
        else:
            https_proxy = 'https://' + https_proxy
        # check all works
        self.get_result(
            connection,
            'yum clean all; ' +
            'https_proxy='' + https_proxy + '' ' +
            yum_test_command,
            timeout=yum_timeout
        )
        # restore firewall
        self.get_return_value(
            connection,
            'service iptables restart'
        )
        return self.log
