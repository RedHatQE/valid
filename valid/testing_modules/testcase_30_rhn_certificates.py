""" This module contains testcase_30_rhn_certificates test """
from valid.valid_testcase import ValidTestcase
from datetime import datetime
import re



def _expiration_date(params):
    """ Get expiration delta in years """
    seven_year_releases = re.compile('^5\.[12345678]$|^6\.[012345]$')

    if seven_year_releases.match(params['version']):
        expiration = 7
    else:
        expiration = 10
    if params['version'].startswith('5.'):
        return datetime(2007 + expiration, 3, 14)
    elif params['version'].startswith('6.'):
        return datetime(2010 + expiration, 11, 10)
    else:
        raise ValueError('release %s unsupported' % params['version'])


class testcase_30_rhn_certificates(ValidTestcase):
    """
    Check for rhn certificates lifetime
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': '5.*|6.*'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        if params['product'].upper() == 'BETA':
            config_rpms = 'rh-amazon-rhui-client rh-amazon-rhui-client-beta'
        else:
            config_rpms = 'rh-amazon-rhui-client'
        cert_files = self.get_result(
            connection,
            'rpm -ql %s | egrep \'.*\.(pem|crt)\'' % config_rpms
        )
        # for each cert file, the notAfter field is examined
        # against the expiration_date and the result is stored in self.log
        try:
            expiration_date = _expiration_date(params)
        except ValueError as err:
            # just log and return in case expiration can't be determined
            self.log.append({'result': 'failure', 'comment': str(err)})
            return self.log
        for cert in cert_files.split():
            date_string = self.get_result(
                connection,
                'openssl x509 -in %s -noout -dates | grep notAfter' % cert
            )
            if date_string and date_string.find('=') != -1:
                cert_expiration = datetime.strptime(
                    # the date_string has the form:
                    #   notAfter=Nov 11 00:00:00 2020 GMT
                    date_string.split('=')[1],
                    '%b %d %H:%M:%S %Y %Z'
                )
                self.log.append(
                    {
                        'result': expiration_date <= cert_expiration
                        and 'passed' or 'failed',
                        'comment': '(%s).notAfter=%s; expecting: %s' %
                        (cert, cert_expiration, expiration_date)
                    }
                )
            else:
                self.log.append({'result': 'failed', 'comment': 'failed to check expiration date for  %s' % cert})

        return self.log
