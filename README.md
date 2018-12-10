carto-report
===========

A Python module to export a database metrics as a html file for CARTO organization user.

Installation
============

You can install carto-report by cloning this repository or by using
[Pip](http://pypi.python.org/pypi/pip):

    pip install carto-report

If you want to use the development version, you can install directly from github:

    pip install -e git+git://github.com/CartoDB/carto-report.git#egg=carto

If using, the development version, you might want to install dependencies as well:

    pip install -r requirements.txt

*Only tested in Python 3*

Usage Example
=============

In this example... TBD

```python
from carto.report import Reporter

reporter = Reporter('CARTO_USER', 'CARTO_ORG', 'API_KEY', STORAGE_MB)
```

Where the signature of the `Reporter` constructor is as follows:

```
Printer(CARTO_USER, CARTO_ORG, API_KEY, STORAGE_MB)
```

Known Issues
============

TBD
