from valid.valid_testcase import *

import StringIO
import ConfigParser
import yaml


class testcase_27_yum_repos(ValidTestcase):
    stages = ["stage1"]
    applicable = {"product": "(?i)RHEL|BETA"}

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        # get repo details file
        self.get_return_value(
            connection,
            '''yum repolist -v all | csplit --prefix=repolist_xx - "%Repo-id\s*:%"''',
            40
        )
        # translate the details into an ini-like structure
        try:
            repos_fp = connection.sftp.open('/root/repolist_xx00')
            repos_details = repos_fp.read()
            repos_fp.close()
        except IOError, e:
            self.log.append({
                "result": "failure",
                "comment": "failed to get actual repo list %s" % e
                })
            return self.log

        # make 'Repo-id : <id>' ini section headers: '[<id>]'
        pattern = re.compile('repo-id\s*:\s*([^\n]*)', re.DOTALL | re.IGNORECASE)
        repos_details = pattern.sub('[\\1]', repos_details)
        # extract particular repos as sections from the structure
        # please note that ConfigParser makes all strings lower case by
        # default
        repos_fp = StringIO.StringIO(repos_details)
        repos_conf = ConfigParser.ConfigParser()
        repos_conf.readfp(repos_fp)
        # convert into a dictionary of {'repo-id':{attr_name:attr_value,...}}
        # this is to be able to compare with expected config dictionary
        # all values would be:
        #   repos = {id:dict(cfg.items(id)) for id in repos_conf.sections()}
        # vaules of interrest:
        #   repos = {id:{'repo-status': repos_conf.get(id, 'repo-status')} for id in repos_conf.sections()}
        repos = {}
        for id in repos_conf.sections():
            repos[id] = {'repo-status': repos_conf.get(id, 'repo-status')}

        # figure out whether expected repos match repos
        with open('/usr/share/valid/data/repos.yaml') as expected_repos_fd:
            all_repos = yaml.safe_load(expected_repos_fd)
        try:
            expected_repos_ = all_repos[params['region']]['%s_%s' % (prod, ver)]
        except KeyError as e:
            self.log.append({
                "result": "skip",
                "comment": "unsupported region and/or product-version combination"
                })
            return self.log
        # expand %region%
        expected_repos = {}
        for k, v in expected_repos_.items():
            expected_repos[k.replace('%region%', params['region'])] = v
        ret = {
            "expected repos": expected_repos,
            "actual repos": repos
        }
        ret['result'] = expected_repos == repos and 'passed' or 'failed'
        self.log.append(ret)
        return self.log
