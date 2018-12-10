# -*- coding: utf-8 -*-
from setuptools import setup

try:
    with open('requirements.txt') as f:
        required = f.read().splitlines()
except:
    required = ['Pillow==5.3.0', 'future==0.16.0']

setup(name="carto-report",
      author="Ramiro Aznar",
      author_email="ramiroaznar@carto.com",
      description="A module to export CARTO user database metrics",
      version="0.0.1",
      url="https://github.com/CartoDB/labs-db-metrics",
      install_requires=required,
      packages=["carto"])
