from valid.valid_testcase import *


class testcase_25_uname(ValidTestcase):
    """
    Check uname output:
    - kernel shoud be equal to latest installed
    - -o shoud return GNU/Linux
    - /etc/sysconfig/kernel shoud contain UPDATEDEFAULT=yes and
       DEFAULTKERNEL=kernel
    """
    stages = ['stage1', 'stage2']
    tags = ['default']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        kernel_ver = None
        uname_r = None

        if prod in ['RHEL', 'BETA']:
            if ver.startswith('5.'):
                uname_r = self.get_result(connection, 'uname -r | sed \'s,\.el5xen,.el5,\'')
                kernel_ver = self.get_result(connection, 'rpm -q --last kernel-xen | sed -e \'s,^kernel-xen-,,\' -e \'s,[[:space:]].*$,,\' | head -1', 30)
            else:
                uname_r = self.get_result(connection, 'uname -r | sed -e \'s,\.i686$,,\'  -e \'s,\.x86_64$,,\'')
                kernel_ver = self.get_result(connection, 'rpm -q --last kernel | sed -e \'s,^kernel-,,\' -e \'s,[[:space:]].*$,,\' | head -1 | sed -e \'s,\.i686$,,\'  -e \'s,\.x86_64$,,\'', 30)
        elif prod == 'FEDORA':
            if ver in ['18', '19', '20'] and params['arch'] == 'i386':
                uname_r = self.get_result(connection, 'uname -r | sed \'s,\.PAE,,\'')
                kernel_ver = self.get_result(connection, 'rpm -q --queryformat \'%{VERSION}-%{RELEASE}.%{ARCH}\n\' kernel-PAE | sort | tail -1', 30)
            else:
                uname_r = self.get_result(connection, 'uname -r')
                kernel_ver = self.get_result(connection, 'rpm -q --queryformat \'%{VERSION}-%{RELEASE}.%{ARCH}\n\' kernel | sort | tail -1', 30)

        if not kernel_ver or not uname_r:
            self.log.append({'result': 'skip', 'comment': 'not applicable for this product/version'})
            return self.log

        uname_o = self.get_result(connection, 'uname -o')
        if uname_r and uname_o and kernel_ver:
            self.get_return_value(connection, '[ %s = %s ]' % (kernel_ver, uname_r))
            self.get_return_value(connection, '[ %s = \'GNU/Linux\' ]' % uname_o)
            if prod in ['RHEL', 'BETA'] and (ver.startswith('5.') or ver.startswith('6.')) and not (ver in ['5.5', '5.6']):
                # No /etc/sysconfig/kernel checks for fedora
                self.get_return_value(connection, 'grep UPDATEDEFAULT=yes /etc/sysconfig/kernel')
                self.get_return_value(connection, 'grep DEFAULTKERNEL=kernel /etc/sysconfig/kernel')
        return self.log
