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
            'yum repolist | grep -i subscription-manager',
            expected_status=1
        )
        # check subscription-manager plugin can be enabled
        pattern = re.compile(
            '.*Loaded plugins:[^\n]*subscription-manager.*',
            re.DOTALL
        )
        self.match(
            'yum --enableplugin=subscription-manager repolist',
            regexp=pattern
        )
        # check system isn't subscribbed
        pattern = re.compile(
            '.*^Status:\s*Not.Subscribed.*',
            re.DOTALL
        )
        self.match('subscription-manager list', regexp.pattern)
