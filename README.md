# carto-report


A Python module to export a database metrics as a html file for CARTO organization user.

## Installation

You can install carto-report by cloning this repository or by using [Pip](http://pypi.python.org/pypi/pip):

```sh
$ pip install carto-report
```

If you want to use the development version, you can install directly from github:

```sh
$ pip install -e git+git://github.com/CartoDB/carto-report.git#egg=carto
```

If using, the development version, you might want to install dependencies as well:

```
$ pip install -r requirements.txt
```

*Only tested in Python 3*

## Usage Example

### Command Line application

The package installs a command line application `carto_report` that has the following usage instructions:

```sh
$ carto_report -h
```
```text
usage: carto_report [-h] [--user-name CARTO_USER] [--api_key CARTO_API_KEY]
                    [--api_url CARTO_API_URL] [--organization CARTO_ORG]
                    [--output OUTPUT] [--quota QUOTA]
                    [--loglevel {DEBUG,INFO,WARNING,ERROR}]

CARTO reporting tool

optional arguments:
  -h, --help            show this help message and exit
  --user-name CARTO_USER, -U CARTO_USER
                        Account user name (defaults to env variable
                        CARTO_USER)
  --api_key CARTO_API_KEY, -a CARTO_API_KEY
                        Api key of the account (defaults to env variable
                        CARTO_API_KEY)
  --api_url CARTO_API_URL, -u CARTO_API_URL
                        Set the base URL. For example:
                        https://username.carto.com/ (defaults to env variable
                        CARTO_API_URL)
  --organization CARTO_ORG, -o CARTO_ORG
                        Set the name of the organization account (defaults to
                        env variable CARTO_ORG)
  --output OUTPUT       File path for the report, defaults to report.html
  --quota QUOTA, -q QUOTA
                        LDS quota for the user, defaults to 5000
  --loglevel {DEBUG,INFO,WARNING,ERROR}, -l {DEBUG,INFO,WARNING,ERROR}
                        How verbose the output should be, default to the most
                        silent
```

### As a python module

```python
from carto_report.report import Reporter

reporter = Reporter(CARTO_USER, CARTO_API_URL, CARTO_ORG, API_KEY, USER_QUOTA)

with open('/tmp/report.html','w') as writer:
    writer.write(reporter.report())
```

Where the different parameters are:

* `CARTO_USER`: user name of the account to check
* `CARTO_API_URL`: this is usually `https://{CARTO_USER}.carto.com/` but may differ if you are not using `carto.com` accounts
* `CARTO_API_KEY`: your CARTO ENGINE master API key
* `USER_QUOTA`: your LDS quota


Known Issues
============

- [x] Improve report layout and style (with Airship).
- [ ] Add assertions.
- [ ] Use conditionals within the template.
- [x] Add debug loggins to bet feedback, especially when getting all tables and analysis.
- [x] Include logging as a proper library.
- [x] Add functions.
- [x] Debug get table sizes section.
