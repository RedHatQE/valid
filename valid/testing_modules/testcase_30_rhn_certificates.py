""" This module contains testcase_30_rhn_certificates test """
from valid.valid_testcase import ValidTestcase
from datetime import datetime
from distutils.version import LooseVersion as Version
import re


def _expiration_date(params):
    """ Get expiration delta in years """
    seven_year_releases = lambda ver: ver >= Version('5.5') and ver <= Version('5.8') or\
                                ver >= Version('6.0') and ver <= Version('6.5')


    if seven_year_releases(params['version']):
        expiration = 7
    else:
        expiration = 10
    version = Version(params['version'])
    if version < '6.0':
        return datetime(2007 + expiration, 3, 14)
    if version < '7.0':
        return datetime(2010 + expiration, 11, 10)
    if version < '8.0':
        return datetime(2014 + expiration, 6, 10)
    raise ValueError('release %s unsupported' % params['version'])


class testcase_30_rhn_certificates(ValidTestcase):
    """
    Check for rhn certificates lifetime
    """
    stages = ['stage1']
    applicable = {'product': '(?i)RHEL|BETA', 'version': 'OS (>= 5.5)'}
    tags = ['default']

    def test(self, connection, params):
        """ Perform test """

        if params['product'].upper() == 'BETA':
            config_rpms = 'rh-amazon-rhui-client rh-amazon-rhui-client-beta'
        else:
            config_rpms = 'rh-amazon-rhui-client'
        cert_files = [cert_file for cert_file in self.get_result(connection, "rpm -ql " + config_rpms).split() \
                        if re.match(r'.*\.(crt|pem)$', cert_file)]
        # for each cert file, the notAfter field is examined
        # against the expiration_date and the result is stored in self.log
        try:
            expiration_date = _expiration_date(params)
        except ValueError as err:
            # just log and return in case expiration can't be determined
            self.log.append({'result': 'failure', 'comment': str(err)})
            return self.log
        for cert in cert_files:
            # the -dates format is:
            # notBefore=Jan 17 10:29:59 2013 GMT
            # notAfter=Jan 17 10:29:59 2014 GMT
            # just the notAfter line is required
            date_string = re.split(
                r'\r?\n',
                self.get_result(connection, 'openssl x509 -in %s -noout -dates' % cert).strip()
            )[-1]
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
