import os
import paramiko
import time
from valid.valid_testcase import *


class testcase_98_package_install_pre(ValidTestcase):
    """
    Do package upgrate with specified package set
    """

    tags = []
    stages = ['stage0']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        self.get_return_value(connection, 'yum check-update ||:', 900)
        if 'pkg' in params:
            rpmfiles = ''
            if type(params['pkg']) == str:
                pkgs_files = [params['pkg']]
            else:
                pkgs_files = params['pkg']

            checklist = []
            for pkg in pkgs_files:
                pkgbase = os.path.basename(pkg)
                connection.sftp.put(pkg, '/tmp/%s' % pkgbase)
                rpmfiles += '/tmp/%s ' % pkgbase
                checklist.append('[ "' + pkgbase + '" = "$(rpm -q --queryformat %{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}.rpm $(rpm -qp --queryformat %{NAME} /tmp/' + pkgbase + '))" ]')
                self.get_return_value(connection, 'ls -l /tmp/%s' % pkgbase)
            if len(pkgs_files) == 1:
                self.get_return_value(connection, 'yum -y --nogpgcheck localinstall %s' % rpmfiles, 900)
            else:
                self.get_return_value(connection, 'rpm -U %s' % rpmfiles, 900)

            for check in checklist:
                self.get_return_value(connection, check)

        else:
            self.log.append({
                    'result': 'skip',
                    'comment': 'no package in parameters, no upgrade was done'
                    })
        return self.log
