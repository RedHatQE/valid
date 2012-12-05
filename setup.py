#!/usr/bin/env python

from setuptools import setup
import glob

setup(name='valid',
    version='0.2',
    description='Image validation (threaded version)',
    author='Vitaly Kuznetsov',
    author_email='vitty@redhat.com',
    url='https://github.com/RedHatQE/valid',
    license="GPLv3+",
    packages=[
        'valid', 'valid.testing_modules'
        ],
    data_files=[
             ('share/valid/hwp', glob.glob('hwp/*.yaml')),
             ('/etc', ['etc/validation.yaml'])
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
