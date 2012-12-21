from valid.valid_testcase import *
import re
_na_versions = re.compile('^5\.[12345678]$|^6\.[123]$')


class testcase_31_subscription_management(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if _na_versions.match(params["version"]):
            self.log.append(
                {
                    "result": "skip",
                    "comment": "N/A for version: %s" % params["version"]
                }
            )
            return self.log
        # check subscription-manager plugin is disabled
        self.ping_pong(
            connection,
            'yum --disablerepo="*" -v repolist',
            expectation='Not loading "subscription-manager" plugin',
            timeout=30
        )
        # check subscription-manager plugin can be enabled
        self.ping_pong(
            connection,
            'yum --enableplugin=subscription-manager --disablerepo="*" -v repolist',
            expectation='Loading "subscription-manager" plugin',
            timeout=30
        )
        # check system isn't subscribbed
        self.ping_pong(
            connection,
            'subscription-manager list',
            expectation='No installed products to list',
            timeout=90
        )
        return self.log
