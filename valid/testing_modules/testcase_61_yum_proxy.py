from valid.valid_testcase import *

class testcase_61_yum_proxy(ValidTestcase):
    stage = ["stage1"]

    def test(self, connection, params):
        try:
            proxy = params["proxy"]
        except KeyError:
            self.log.append({'result': 'skip', 'comment': 'No proxy set'})
            return self.log
        # update rh-amazon-rhui-client
        # the repo id is: rhui-<region>-client-config-server-<major version nr>
        self.get_return_value(
            connection,
            "yum --disablerepo=* --enablerepo " +
            "rhui-%s-client-config-server-%s" % (params['region'],
                params['version'].split('.')[0] +
            "update -y"
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
                "iptables -I OUTPUT -d %s -j DROP" % cds
            )
        # read the yum.conf
        # and provide the proxy setup
        try:
            yum_conf_fp = connection.sftp.open('/etc/yum.conf')
            yum_conf_data = yum_conf_fp.read()
            yum_conf_fp.close()
        except IOError, e:
            self.log.append({
                "result": "failure",
                "comment": "failed to get actual repo list %s" % e
                })
        finally:
            return self.log
        # read as INI
        yum_conf_fp = StringIO.StringIO(yum_conf_data)
        yum_conf = ConfigParser.ConfigParser()
        import copy
        yum_conf_data_old = copy.deepcopy(yum_conf_data)
        try:
            yum_conf.readfp(yum_conf_fp)
        except: Exception as e
            self.log.append({
                "result", "failure",
                "comment", "failed parsing yum.conf: %s" % e
            })
        finally:
            return self.log
        # provide the proxy config details
        if 'port' in proxy:
            yum_conf.set('main', 'proxy', "https://" + proxy['host'] +
                         ":" + proxy['port'])
        else:
            yum_conf.set('main', 'proxy', "https://" + proxy['host'])
        if 'user' in proxy:
            yum_conf.set('main', 'proxy_username', proxy['user'])
        if 'password' in proxy:
            yum_conf.set('main', 'proxy_password', proxy['password'])
        # write the data back
        try:
            yum_conf_fp = connection.sftp.open('/etc/yum.conf', 'w+')
            yum_conf.write(yum_conf_fp)
            yum_conf_fp.close()
        except Error as e:
            self.log({
                "result", "failure",
                "comment", "couldn't write '/etc/yum.conf': %s" % e
            })
        finally:
            return self.log
        # test all works
        self.get_return_value(
            connection,
            "yum clean all; yum repolist"
        )
        # restore original yum conf
        try:
            yum_conf_fp = connection.sftp.open('/etc/yum.conf', 'w+')
            yum_conf_fp.write(yum_conf_data_old)
            yum_conf_fp.close()
        except Error as e:
            self.log({
                "result", "failure",
                "comment", "couldn't write '/etc/yum.conf': %s" % e
            })
        finally:
            return self.log
        # try the same with an env variable
        if 'port' in proxy:
            https_proxy=proxy['host'] + ":" + proxy['port']
        if 'user' in proxy and 'password' in proxy:
            https_proxy="https://" + proxy['user'] + ":" + proxy['password'] +
                        "@" + https_proxy
        else
            https_proxy="https://" + https_proxy
        # check all works
        self.get_return_value(
            connection,
            "yum clean all; " +
            "https_proxy=" + https_proxy + " " +
            "yum repolist"
        )
        # restore firewall
        self.get_return_value(
            connection,
            "service iptables restart"
        )






