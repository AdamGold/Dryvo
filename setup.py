from setuptools import setup, find_packages

setup(name='dryvo',
      version='0.1.3',
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
          'Flask-OAuth'
      ],
      zip_safe=False)
