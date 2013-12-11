from valid.valid_testcase import *

import StringIO
import ConfigParser
import yaml


class testcase_27_yum_repos(ValidTestcase):
    """
    Check for enabled yum repos
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA'}
    not_applicable = {"product": "(?i)RHEL|BETA", "version": "6.0"}
    tags = ['default']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        if connection.rpyc is None:
            self.log.append({
                'result': 'failure',
                'comment': 'test can\'t be performed without RPyC connection'})
            return self.log
        repos = {}
        rb = connection.rpyc.modules.yum.YumBase()
        for repo in rb.repos.repos:
            repos[repo] = rb.repos.repos[repo].isEnabled()

        # figure out whether expected repos match repos
        with open('/usr/share/valid/data/repos.yaml') as expected_repos_fd:
            all_repos = yaml.safe_load(expected_repos_fd)
        try:
            expected_repos_ = all_repos[params['region']]['%s_%s' % (prod, ver)]
        except KeyError as e:
            self.log.append({
                'result': 'skip',
                'comment': 'unsupported region and/or product-version combination'})
            return self.log
        # expand %region%
        expected_repos = {}
        for k, v in expected_repos_.items():
            expected_repos[k.replace('%region%', params['region'])] = v
        ret = {
            'expected repos': expected_repos,
            'actual repos': repos
        }
        ret['result'] = expected_repos == repos and 'passed' or 'failed'
        self.log.append(ret)
        return self.log
