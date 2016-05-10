#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'jsonschema',
    'werkzeug',
    'strict_rfc3339',
]

test_requirements = [
    'flask',
    'pytest',
    'mock',
    'enum34',
    'hypothesis',
    'pytest-xdist',
    'sphinx_rtd_theme'
]

setup(
    name='spectastic',
    version='0.2.5',
    description="Request and response validation compatible with swagger.",
    long_description=readme + '\n\n' + history,
    author="Jacob Straszynski",
    author_email='jacob.straszynski@planet.com',
    url='https://github.com/planetlabs/spectastic',
    packages=[
        'spectastic',
    ],
    package_dir={'spectastic':
                 'spectastic'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache 2",
    zip_safe=False,
    keywords='spectastic',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
