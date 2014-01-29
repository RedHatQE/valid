""" This module contains testcase_27_yum_repos test """
from valid.valid_testcase import ValidTestcase

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
        """ Perform test """

        prod = params['product'].upper()
        ver = params['version']
        if connection.rpyc is None:
            self.log.append({
                'result': 'failure',
                'comment': 'test can\'t be performed without RPyC connection'})
            return self.log
        repos = {}
        rbase = connection.rpyc.modules.yum.YumBase()
        for repo in rbase.repos.repos:
            repos[repo] = rbase.repos.repos[repo].isEnabled()

        # figure out whether expected repos match repos
        with open(self.datadir + '/repos.yaml') as expected_repos_fd:
            all_repos = yaml.safe_load(expected_repos_fd)
        try:
            expected_repos_ = all_repos[params['region']]['%s_%s' % (prod, ver)]
        except KeyError:
            self.log.append({
                'result': 'skip',
                'comment': 'unsupported region and/or product-version combination'})
            return self.log
        # expand %region%
        expected_repos = {}
        for key, val in expected_repos_.items():
            expected_repos[key.replace('%region%', params['region'])] = val
        ret = {
            'expected repos': expected_repos,
            'actual repos': repos
        }
        ret['result'] = expected_repos == repos and 'passed' or 'failed'
        self.log.append(ret)
        return self.log
