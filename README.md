Image validation
================

Contents
--------
    data/
          some data for testing (e.g. package lists)
    etc/
          validation.yaml - example configuration (AWS credentials, keys, ...)
    examples/
          validation examples
    hwp/
          hardware profiles
    scripts/
          valid_runner.py - main validation runner
    valid/
          source code


Usage example
-------------
Example: valid_runner.py --data examples/example_rhel63_58_all_x86_64.yaml


Server mode
-----------
Validation can be done in client/server mode as well. The communications are secured with HTTPS (default
port is 8080). You can create certificates using 'valid_cert_creator.py' script. You should use real hostname
you'll be connecting to, it will be checked during ssl negotiations. Client certificate and key are generated
in /etc/valid/ directory.
On server side:
'valid_runner.py --server' (or use provided systemd valid.service)

On client side:
valid_client.py --cert 'certfile' --key 'keyfile' --host 'hostname' --add 'datafile' [ --emails 'comma-separated email list']
you'll get the transaction id.

and then
valid_client.py	--cert 'certfile' --key	'keyfile' --host 'hostname' --get 'transaction id'


Requirements
------------
Python-patchwork library is required. You can get it here: https://github.com/RedHatQE/python-patchwork or
you can alternatively download prebuilt RPM here: https://rhuiqerpm.s3.amazonaws.com/index.html


Writing tests
-------------
There are some examples in valid/testing_modules directory. The test is a class which looks like this:

valid/testing_modules/testcase_xx_testname.py:

    from valid.valid_testcase import *
    
    
    class testcase_xx_testname(ValidTestcase):
        # applicable stages
        stages = ["stage1"]
	# applicable setups
	applicable = {"product": "(?i)RHEL|BETA", "version": "5.*|6.*"}

        def test(self, connection, params):
	    # doing testing

'connection' is a patchwork.connection.Connection object.
'params' is a data line united with hardware profile and runtime information (so you can use something like
params["memory"], params["product"], ...)

Don't forget to include your new test in valid/testing_modules/__init__.py. Tests are executed in alphabetical
order.

Prebuil RPMs
------------
Prebuilt RPMs are available here: https://rhuiqerpm.s3.amazonaws.com/index.html
