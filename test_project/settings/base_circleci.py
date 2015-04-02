import os
exec(
    compile(
        open(os.path.join(os.path.dirname(__file__), 'base.py')).read(),
        os.path.join(os.path.dirname(__file__), 'base.py'),
        'exec'
    )
)


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        "NAME": "circle_test",
        "USER": "ubuntu",
        "PASSWORD": "",
    },
}
