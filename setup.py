#!/usr/bin/env python

from setuptools import setup
import glob

setup(name='valid',
    version='0.6',
    description='Image validation (threaded version)',
    author='Vitaly Kuznetsov',
    author_email='vitty@redhat.com',
    url='https://github.com/RedHatQE/valid',
    license="GPLv3+",
    packages=[
        'valid', 'valid.testing_modules', 'valid.cloud'
        ],
    data_files=[
             ('share/valid/hwp', glob.glob('hwp/*.yaml')),
             ('share/valid/data', glob.glob('data/*')),
             ('share/valid/examples', glob.glob('examples/*.yaml')),
             ('/etc', ['etc/validation.yaml']),
             ('/etc/valid', ['etc/setup_script.sh']),
             ('/etc/sysconfig', ['etc/valid'])
    ],
    classifiers=[
            'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
            'Programming Language :: Python',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Operating System :: POSIX',
            'Intended Audience :: Developers',
            'Development Status :: 4 - Beta'
    ],
    scripts=glob.glob('scripts/*.py') + glob.glob('scripts/*.sh')
)
