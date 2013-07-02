from distutils.core import setup

setup(
    name='narrative',
    version='0.1',
    packages=[
        'narrative',
        'narrative.migrations',
    ],
    url='https://github.com/',
    description='Django narrative',
    install_requires=[
        'django>=1.4',
    ]
)
