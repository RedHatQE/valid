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
        self.get_return_value(
            connection,
            'yum --disablerepo="*" repolist | grep -i subscription-manager',
            expected_status=1
        )
        # check subscription-manager plugin can be enabled
        self.ping_pong(
            connection,
            'yum --enableplugin=subscription-manager --disablerepo="*" repolist',
            expectation='Loaded plugins:[^\n]*subscription-manager'
        )
        # check system isn't subscribbed
        self.ping_pong(
            connection,
            'subscription-manager list',
            expectation='Status:\s*Not.Subscribed'
        )
        return self.log
