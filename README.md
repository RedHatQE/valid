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
You can run validation runner in 'server' mode using --server switch. Status webpage will be accessible
on 0.0.0.0:8080


Requirements
------------
Python-patchwork library is required. You can get it here: https://github.com/RedHatQE/python-patchwork or
you can alternatively download prebuilt RPM here: https://rhuiqerpm.s3.amazonaws.com/index.html


Prebuil RPMs
------------
Prebuilt RPMs are available here: https://rhuiqerpm.s3.amazonaws.com/index.html
