import os
exec(
    compile(
        open(os.path.join(os.path.dirname(__file__), 'base.py')).read(),
        os.path.join(os.path.dirname(__file__), 'base.py'),
        'exec'
    )
)
