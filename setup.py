from distutils.core import setup

setup(
    name='narrative',
    version='0.2.2',
    packages=[
        'narrative',
        'narrative.management',
        'narrative.management.commands',
    ],
    url='https://github.com/',
    description='Django narrative',
    install_requires=[
        'django>=1.4',
    ]
)
