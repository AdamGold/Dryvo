from setuptools import setup, find_packages

setup(name='drivapp',
      version='0.1',
      description='Drivapp Application',
      url='https://bitbucket.org/drivapp',
      author='Drivapp',
      author_email='',
      license='MIT',
      packages=find_packages(),
      install_requires=[
          'gunicorn',
          'psycopg2',
          'SQLAlchemy',
          'sqlalchemy-utils',
          'Flask',
          'flask-login',
          'flask-sqlalchemy',
          'flask-script'
      ],
      zip_safe=False)
