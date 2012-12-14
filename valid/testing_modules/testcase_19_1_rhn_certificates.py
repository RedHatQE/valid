from valid.valid_testcase import *
from datetime import datetime
import re
_seven_year_releases = re.compile('^5\.[12345678]$|^6\.[123]$')


def _expiration_date(params):
    # get expiration delta in years
    if _seven_year_releases.match(params["version"]):
        expiration = 7
    else:
        expiration = 10
    if params["version"].startswith("5."):
        return datetime(2007 + expiration, 3, 14)
    elif params["version"].startswith("6."):
        return datetime(2010 + expiration, 11, 10)
    else:
        raise ValueError("release %s unsupported" % params["version"])


class testcase_19_1_rhn_certificates(ValidTestcase):
    stages = ["stage1"]

    def test(self, connection, params):
        if params["product"].upper() == 'BETA':
            config_rpms = "rh-amazon-rhui-client rh-amazon-rhui-client-beta"
        else:
            config_rpms = "rh-amazon-rhui-client"
        cert_files = self.get_result(
            connection,
            "rpm -ql %s | egrep '.*\.(pem|crt)'" % config_rpms
        )
        # for each cert file, the notAfter field is examined
        # against the expiration_date and the result is stored in self.log
        try:
            expiration_date = _expiration_date(params)
        except ValueError as e:
            # just log and return in case expiration can't be determined
            self.log.append({"result": "failure", "comment": str(e)})
            return
        results = []
        for cert in cert_files.split():
            date_string = self.get_result(
                connection,
                'openssl x509 -in %s -noout -dates | grep notAfter' % file
            )
            cert_expiration = datetime(
                # the date_string has the form:
                #   notAfter=Nov 11 00:00:00 2020 GMT
                date_string.split('=')[1],
                '%b %d %H:%M:%S %Y %Z'
            )
            self.log.append(
                {
                    "result": expiration_date <= cert_date
                    and 'passed' or 'failed',
                    "comment": "(%s).notAfter=%s; expecting: %s" %
                    (cert, cert_expiration, expiration_date)
                }
            )
        return self.log

__all__ = ["testcase_19_1_rhn_certificates"]
