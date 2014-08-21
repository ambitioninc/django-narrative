from setuptools import setup

setup(
    name='django-narrative',
    version='0.5.9',
    packages=[
        'narrative',
        'narrative.batteries',
        'narrative.migrations',
        'narrative.management',
        'narrative.management.commands',
    ],
    url='https://github.com/',
    description='Django narrative',
    install_requires=[
        'django>=1.4',
        'django-manager-utils>=0.3.6',
        'django-tastypie>=0.11.0',
        'pytz>=2012h',
    ]
)
