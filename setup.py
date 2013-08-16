from distutils.core import setup

setup(
    name='narrative',
    version='0.3.5.1',
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
    ]
)
