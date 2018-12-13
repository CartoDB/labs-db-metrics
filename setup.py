# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

try:
    with open('requirements.txt') as f:
        required = f.read().splitlines()
except:
    required = ['Pillow==5.3.0', 'future==0.16.0']

setup(name="carto-report",
      author="Ramiro Aznar",
      author_email="ramiroaznar@carto.com",
      description="A module to export CARTO user database metrics",
      long_description=read('README.md'),
      long_description_content_type="text/markdown",
      keywords = "carto cli cartodb api reporting postgres",
      license="BSD",
      classifiers=[
          "License :: OSI Approved :: BSD License",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.7",
      ],
      version="0.0.1",
      url="https://github.com/CartoDB/labs-db-metrics",
      install_requires=required,
      packages=find_packages(),
      include_package_data=True,
      entry_points='''
[console_scripts]
carto_report=carto_report.cli:main
      ''')
