## Submitting Contributions

Contributions are totally welcome. However, contributors must sign a Contributor License Agreement (CLA) before making a submission. [Learn more here.](https://carto.com/contributing)

## Release process

 Prepare a `~/.pypirc` file:

```
[distutils]
index-servers =
  pypi
  pypitest

[pypi]
username=your_username
password=your_password

[pypitest]
repository: https://test.pypi.org/legacy/
username=your_username
password=your_password
```

**Note:** You must be maintainer at carto-report pypi repo.



1. Update version number (`VERSION`) and information at `setup.py` and `NEWS.md`.
2. Create a tag, for example with `git tag v0.0.3; git push --tags`
3. Generate the package with `python setup.py sdist`, it will create a file at `dist/carto-report-VERSION.tar.gz`
5. Upload the package to the test repository: `twine upload --repository pypitest dist/carto-report-VERSION.tar.gz`
6. Install it in a **clean** environment: `pip install --index-url=https://test.pypi.org/simple --extra-index-url=https://pypi.org/simple carto-report`.
7. **Test it**.
8. Release it: `twine upload dist/carto-report-VERSION.tar.gz`.
