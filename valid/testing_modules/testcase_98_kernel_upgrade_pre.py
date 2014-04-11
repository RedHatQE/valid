""" This module contains testcase_98_kernel_upgrade_pre test """
import os
import paramiko
import time
from valid.valid_testcase import ValidTestcase


class testcase_98_kernel_upgrade_pre(ValidTestcase):
    """
    Do kernel upgrate (with specified package set or from repo) before testing
    """

    tags = ['kernel', 'preinstall_kernel']
    stages = ['stage0']

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version']
        if (prod in ['RHEL', 'BETA']) and (ver.startswith('6.')):
            # remove bfa-firmware - conflicts with new RHEL6 kernel
            self.get_return_value(connection, 'rpm -q bfa-firmware && rpm -e bfa-firmware ||:', 60)
        if 'kernelpkg' in params:
            kernelfiles = ''
            if type(params['kernelpkg']) == str:
                pkgs_files = [params['kernelpkg']]
            else:
                pkgs_files = params['kernelpkg']
            for pkg in pkgs_files:
                pkgbase = os.path.basename(pkg)
                connection.sftp.put(pkg, '/tmp/%s' % pkgbase)
                kernelfiles += '/tmp/%s ' % pkgbase
                self.get_return_value(connection, 'ls -l /tmp/%s' % pkgbase)
            if len(pkgs_files) == 1:
                self.get_return_value(connection, 'yum -y update %s' % kernelfiles, 900)
                kernel_updated = self.get_return_value(connection, '[ $(rpm -qa kernel | wc -l) -gt 1 ]', nolog=True)
            else:
                kernel_updated = self.get_return_value(connection, 'rpm -U %s' % kernelfiles, 900)
        else:
            # doing upgrade from repo
            self.get_return_value(connection, 'yum -y install kernel', 300)
            kernel_updated = self.get_return_value(connection, '[ $(rpm -qa kernel | wc -l) -gt 1 ]', nolog=True)
        if kernel_updated == 0:
            if prod == 'FEDORA' and ver == '18':
                # we have a bug in kernel upgrade
                # pylint: disable=C0301
                self.get_result(connection, 'cat /boot/grub/grub.conf | sed -e \'s|hd0,0|hd0|\' -e \'s|default=1|default=0|\' > /boot/grub/menu.lst && echo SUCCESS')
            self.get_return_value(connection, 'nohup sleep 1s && nohup reboot &')
            time.sleep(30)
        else:
            self.log.append({'result': 'skip',
                             'comment': 'no kernel upgrade was done'})
        return self.log
