from setuptools import setup, find_packages

setup(name='dryvo',
      version='0.1.8',
      description='Dryvo Application',
      url='https://bitbucket.org/dryvo',
      author='Dryvo',
      author_email='',
      license='MIT',
      packages=find_packages(),
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
      zip_safe=False)
