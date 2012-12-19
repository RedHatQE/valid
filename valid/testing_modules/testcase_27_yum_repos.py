from valid.valid_testcase import *

import StringIO
import ConfigParser
import yaml


class testcase_27_yum_repos(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"]
        # get repo details file
        self.get_return_value(
            connection,
            "yum repolist -v all | csplit --prefix=repolist_xx - '%pkgsack time:%1'",
            40
        )
        # translate the details into an ini-like structure
        repos_details = self.get_result(
           connection,
           "head -n-1 repolist_xx00 | sed -e 's/Repo-id\s*:\s*\(.*\)/[\1]/'"
        )
        # extract particular repos as sections from the structure
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
        expected_repos = all_repos[params['region']]['%s-%s' % (prod, ver[0])]
        ret = {
            "comment": "# expected repos:\n%s\n# actual repos:\n%s" %
                (yaml.dump(expected_repos), yaml.dump(repos))
        }
        ret['result'] = expected_repos == repos and 'passed' or 'failed'
        self.log.append(ret)
        return self.log
