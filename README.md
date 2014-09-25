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
Example: 

`valid_runner.py --data examples/example_rhel63_58_all_x86_64.yaml`

Note
----
Please note `Valid` isn't maintained any more.
You might consider using [dva](https://github.com/RedHatQE/dva) istead.

Data files
----------
Data file is a yaml-encoded list. Example:

examle_datafile.yaml:

    - ami: ami-bafcf3ce
      arch: x86_64_bug914737
      product: Fedora
      region: eu-west-1
      version: '18'

Mandatory fileds:
* ami: AMI id
* arch: name of hwp file (/usr/share/valid/hwp/<name>.yaml)
* product: product name ("RHEL", "Fedora", ...)
* version: product version (e.g. "18", "6.3", ...)

Optional fields:
* cloud: cloud driver to use ('ec2', 'openstack')
* name: name tag for testing
* disable_stages: disable specified stages
* enable_stages: enable specified stages only (overrides disable_stages)
* disable_tags: disable specified tags
* enable_tags: enable specified tags only (overrides disable_stages)
* disable_tests: disable specified tests
* enable_tests: enable specified tests only (overrides disable_stages)
* repeat: repeat testing with the same instance N times
* keepalive: do not terminate the instance after testing (true/false)

EC2-specific mandatory fields:
* region: EC2 region name
* itype: Instance type ("hourly", "access")

Data file is being updated by hwp data!


HWP files
---------
HWP file is also a yaml-encoded list. Example:

x86_64_hvm_kernel.yaml:

    - arch: x86_64
      cpu: '2'
      cloudhwname: m3.xlarge
      memory: '7000000'
      virtualization: hvm
    - arch: x86_64
      bmap:
      - {delete_on_termination: true, name: /dev/sda1, size: '15'}
      - {ephemeral_name: ephemeral0, name: /dev/sdf}
      cpu: '32'
      cloudhwname: cr1.8xlarge
      memory: '244000000'
      virtualization: 'hvm'

Mandatory fields:
* arch: hardware architecture ("x86_64", "i386")
* cloudhwname: EC2 instance name ("t1.micro", "m3.xlarge", ...)
* cpu: expected numer of CPUs
* memory: expected amount of memory
* virtualization: virtualization type ("hwp", "paravirtual")

Optional fields:
* bmap: block device map
* userdata: userdata string


Useful tools
------------
There are several useful tools available:
* `valid_bugzilla_reporter.py` - examine result, report to bugzilla (--test option is useful as well)
* `valid_debug_run.py` - run one specified test on existing instance


Requirements
------------
`python-paramiko`, `python-rpyc`, and `python-boto` are required.

Server mode
-----------
Validation can be done in client/server mode as well. The communications are secured with HTTPS (default
port is 8080). You can create certificates using `valid_cert_creator.py` script. You should use real hostname
you'll be connecting to, it will be checked during ssl negotiations. Client certificate and key are generated
in /etc/valid/ directory.

* On server side:

`valid_runner.py --server` (or use provided systemd valid.service)

* On client side:

`valid_client.py --cert 'certfile' --key 'keyfile' --host 'hostname' --add 'datafile' [ --emails 'comma-separated email list']`
you'll get the transaction id.

* And then:

`valid_client.py --cert 'certfile' --key 'keyfile' --host 'hostname' --get 'transaction id'`


Writing tests
-------------
There are some examples in valid/testing_modules directory. The test is a class which looks like this:

valid/testing_modules/testcase_xx_testname.py:

    from valid.valid_testcase import *


    class testcase_xx_testname(ValidTestcase):
        # applicable stages
        stages = ["stage1"]
	# testing tags
	tags = ["default"]
	# applicable setups
	applicable = {"product": "(?i)RHEL|BETA", "version": "5.*|6.*"}

        def test(self, connection, params):
	    # doing testing

* 'connection' is a valid.valid_connection.ValidConnection object.
* 'params' is a data line united with hardware profile and runtime information (so you can use something like params["memory"], params["product"], ...)
* Setting "stages" and "tags" is mandatory. Don't forget to include your new test in `valid/testing_modules/__init__.py`.
* Tests are executed in alphabetical order with repetition count and stage name as prefix (e.g. 01stage1testcase_xx_testname).


Custom 3rd-party test cases as validation plugins
-------------------------------------------------
It is possible to add custom 3rd-party test cases. These have to sub-class `valid.valid_testcase.ValidTestcase`.
To register the 3rd-party test cases to valid, provide  `valid.testing_modules` entry points in setup.py:
```
setup(name='custom_valid_testcases_module',
       version=0.1,
       description='custom valid testcase module',
       install_requires=['valid >= 0.6'],
       packages=['custom_valid', 'custom_valid.testing_modules'],
       entry_points={
           'valid.testing_modules.my_module': ['my_module = custom_valid.testing_modules.my_module'],
      },
)
```

Prebuilt RPMs
------------
Prebuilt RPMs are available here: https://rhuiqerpm.s3.amazonaws.com/index.html
