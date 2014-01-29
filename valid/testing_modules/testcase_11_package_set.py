""" This module contains testcase_11_package_set test """
import os
import re
from valid.valid_testcase import ValidTestcase


class testcase_11_package_set(ValidTestcase):
    """
    Check that all packages specified in list
    /usr/share/valid/data/packages_<name>  are present
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA|FEDORA'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        packages = self.match(connection,
                              'rpm -qa --queryformat \'%{NAME},\' && echo',
                              re.compile('.*\r\n(.*),\r\n.*', re.DOTALL),
                              timeout=30)
        if packages:
            basepath = self.datadir + '/packages_'
            path = ''
            if params['product'].upper() == 'FEDORA':
                basepath += 'fedora_'
                if os.path.exists(basepath + params['version']):
                    path = basepath + params['version']
            else:
                basepath += 'rhel_'
                if (len(params['version']) > 2) and os.path.exists(basepath + params['version'][0] + params['version'][2:]):
                    path = basepath + params['version'][0] + params['version'][2:]
                elif (len(params['version']) > 0) and os.path.exists(basepath + params['version'][0]):
                    path = basepath + params['version'][0]
            if path == '':
                self.log.append({'result': 'skip', 'comment': 'no package set for this os version'})
                return self.log
            with open(path, 'r') as psetfile:
                package_set_requred = set(psetfile.read().split('\n')[:-1])
            package_set_got = set(packages[0].split(','))
            if params['userdata'].find('yum -y install xdelta') != -1:
                # package was installed by cloud-init
                package_set_got.discard('xdelta')
            difference = package_set_requred.difference(package_set_got)
            difference_new = package_set_got.difference(package_set_requred)
            self.log.append({'result': 'passed', 'comment': 'Newly introduced packages: ' + str(sorted(list(difference_new)))})
            if params['product'].upper() == 'BETA' and len(difference) > 1:
                self.log.append({'result': 'failed', 'comment': 'Beta may lack not more than 1 package: ' + str(sorted(list(difference)))})
            elif len(difference) > 1:
                self.log.append({'result': 'failed', 'comment': 'some packages are missing: ' + str(sorted(list(difference)))})
            else:
                self.log.append({'result': 'passed', 'comment': 'All required package are included'})
        return self.log
