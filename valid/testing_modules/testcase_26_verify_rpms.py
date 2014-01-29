""" This module contains testcase_26_verify_rpms test """
import yaml
from valid.valid_testcase import ValidTestcase


class testcase_26_verify_rpms(ValidTestcase):
    """
    Do rpm -Va and compare the number of packages with modified files
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version']

        if connection.rpyc is None:
            self.log.append({
                'result': 'failure',
                'comment': 'test can\'t be performed without RPyC connection'})
            return self.log

        modified_files = {}

        cmd = ("/bin/sh", "-c", "rpm -Va --nomtime --nosize --nomd5; exit 0")
        if list(connection.rpyc.modules.sys.version_info)[1] >= 6:
            # python 2.6 - 2.7
            cmd = list(cmd)

        proc = connection.rpyc.modules.subprocess.Popen(cmd, stdout=connection.rpyc.modules.subprocess.PIPE, stderr=connection.rpyc.modules.subprocess.PIPE)
        out, _ = proc.communicate()
        if proc.returncode != 0:
            self.log.append({
                'result': 'failure',
                'comment': 'failed to get rpm -Va result from host, error %s' % proc.returncode})
            return self.log

        files = out.split('\n')

        for fline in files:
            pos = fline.find('/')
            if pos != -1:
                modified_files[fline[pos:]] = True

        with open(self.datadir + '/verify_rpms.yaml') as expected_modified_fd:
            all_modified = yaml.safe_load(expected_modified_fd)
        try:
            expected_modified = all_modified['%s_%s' % (prod, ver)]
        except KeyError:
            self.log.append({
                'result': 'skip',
                'comment': 'unsupported region and/or product-version combination'})
            return self.log

        ret = {
            'expected modified files': expected_modified,
            'actual modified files': modified_files
        }

        ret['result'] = expected_modified == modified_files and 'passed' or 'failed'
        self.log.append(ret)

        return self.log
