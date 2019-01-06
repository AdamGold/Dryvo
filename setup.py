from setuptools import setup, find_packages

test_req = ['pytest==4.0.2', 'pytest-flask==0.14.0', 'pytest-cov==2.6.0',
            'responses==0.9.0', "coverage==4.5.2", "testing.postgresql"]

setup(name='dryvo',
      version='0.2',
      description='Dryvo Application',
      url='https://bitbucket.org/dryvo',
      author='Dryvo',
      author_email='',
      license='MIT',
      packages=['server'],
      install_requires=[
          'gunicorn',
          'SQLAlchemy',
          'sqlalchemy-utils',
          'Flask',
          'flask-login',
          'flask-sqlalchemy',
          'flask-script',
          'flask-session',
          'pyjwt==1.4.2'
      ],
      tests_require=test_req,
      setup_requires=['pytest-runner==4.2'],
      extras_require={
          'test': test_req
      },
      zip_safe=False)
