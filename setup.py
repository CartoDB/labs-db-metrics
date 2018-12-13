# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
import os


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


try:
    with open('requirements.txt') as f:
        required = f.read().splitlines()
except:
    required = ['carto==1.4', 'mpld3==0.3', 'jinja2==2.10',
                'numpy==1.15.1', 'pandas==0.23.4', 'matplotlib==2.2.3']

setup(name="carto-report",
      author="Ramiro Aznar, Jorge Sanz",
      author_email="ramiroaznar@carto.com, jsanz@carto.com",
      description="A module to export CARTO user database metrics",
      long_description=read('README.md'),
      long_description_content_type="text/markdown",
      keywords="carto cli cartodb api reporting postgres",
      license="BSD",
      classifiers=[
          "License :: OSI Approved :: BSD License",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.7",
      ],
      version="0.0.2",
      url="https://github.com/CartoDB/labs-db-metrics",
      install_requires=required,
      packages=find_packages(),
      include_package_data=True,
      entry_points='''
[console_scripts]
carto_report=carto_report.cli:main
      ''')
