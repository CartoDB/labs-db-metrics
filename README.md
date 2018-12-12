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
from carto_report.report import Reporter

reporter = Reporter('CARTO_USER', 'CARTO_API_URL', 'CARTO_ORG', 'API_KEY', USER_QUOTA)

with open('/tmp/report.html','w') as writer:
    writer.write(reporter.report())
```

Where the signature of the `Reporter` constructor is as follows:

```
Reporter(CARTO_USER, CARTO_API_URL, CARTO_ORG, API_KEY, USER_QUOTA)
```

Known Issues
============

- [ ] Improve report layout and style (with Airship).
- [ ] Add assertions.
- [ ] Use conditionals within the template.
- [ ] Add debug loggins to bet feedback, especially when getting all tables and analysis.
- [ ] Include logging as a proper library.
