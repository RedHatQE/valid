""" This module contains testcase_62_cpuflags test """
from valid.valid_testcase import ValidTestcase
from distutils.versionpredicate import VersionPredicate


class testcase_62_cpuflags(ValidTestcase):
    """
    Check various cpu flags
    """
    stages = ['stage1', 'stage2']
    tags = ['default', 'kernel']
    applicable = {'virtualization': 'hvm', 'product': 'BETA|RHEL'}

    def test(self, connection, params):
        """ Perform test """
        if not VersionPredicate('RHEL (>= 6.6)').satisfied_by(params['version']):
            self.log.append({'result': 'skip', 'comment': 'not applicable for this product/version'})
            return self.log

        # https://bugzilla.redhat.com/show_bug.cgi?id=1061348
        self.get_return_value(connection, 'grep ^flags /proc/cpuinfo | grep "[^a-z0-9]avx[^a-z0-9]"')
        self.get_return_value(connection, 'grep ^flags /proc/cpuinfo | grep "[^a-z0-9]xsave[^a-z0-9]"')

        return self.log
