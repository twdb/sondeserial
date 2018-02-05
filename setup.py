from setuptools import setup, find_packages

setup(
    name='serialsonde',
    packages=find_packages(),
    version='1.0.0',
    description=('Tools for interacting with YSI datasondes via serial'
                 'connection'),
    author='Taylor Sansom',
    author_email='taylor.sansom@twdb.texas.gov',
    url='http://github.com/twdb/sondeserial',
    keywords=['serial', 'sonde'],
    license='MIT License',
)
