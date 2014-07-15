""" This module contains testcase_31_subscription_management test """
from valid.valid_testcase import ValidTestcase


class testcase_31_subscription_management(ValidTestcase):
    """
    Subscription manager shoud be disabled
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': r'(?!^5\.[123456789]$|^6\.[01234]$)'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        # check subscription-manager plugin is disabled
        self.ping_pong(
            connection,
            'yum --disablerepo=\'*\' -v repolist',
            expectation='Not loading "subscription-manager" plugin',
            timeout=30
        )
        # check subscription-manager plugin can be enabled
        self.ping_pong(
            connection,
            'yum --enableplugin=subscription-manager --disablerepo=\'*\' -v repolist',
            expectation='Loading "subscription-manager" plugin',
            timeout=30
        )
        if params['version'].startswith('5.'):
            # RHEL5.* is going to be updated to match newer major versions gradually
            result = self.ping_pong(
                connection,
                'subscription-manager list',
                expectation='Installed Product Status',
                timeout=90
            )
            if result == 'failed':
                # warn in case there's no subscription shown
                self.log[-1]['result'] = 'warning'
        else:
            self.ping_pong(
                connection,
                'subscription-manager list',
                expectation='Installed Product Status',
                timeout=90
            )
        return self.log
