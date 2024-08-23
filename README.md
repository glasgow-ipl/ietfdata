[ietfdata](https://github.com/glasgow-ipl/ietfdata) - Access the IETF Datatracker and related resources
=============================================================

This project contains Python 3 libraries to interact with, and
access, the [IETF datatracker](https://datatracker.ietf.org), 
[RFC index](https://www.rfc-editor.org), and related resources.


Getting started
---------------

The project uses Pipenv for dependency management. To begin, run:
```~~~~~~~~
pipenv install --dev -e .
```
to create a Python virtual environment with appropriate packages install.
Then, run:
```~~~~~~~~
pipenv shell
```
to start the virtual environment, within which you can run the scripts.

Once the virtual environment is started, running:
```~~~~~~~~
python3 tests/test_datatracker.py 
```
will run the test suite for the datatracker module. Running:
```~~~~~~~~
python3 tests/test_rfcindex.py
```
Will test the rfcindex module.


Caching
-------

The ietfdata library can use a
[MongoDB](https://docs.mongodb.com/manual/administration/install-community/)
instance as a cache. Using a cache reduces the number of requests that are made
directly to the Datatracker, improving performance, and reducing the impact on
the IETF's infrastructure. While using a cache is optional when accessing the
Datatracker, it is required when accessing the mail archive.

The hostname, port, username, and password for the MongoDB instance that is to
be used as the cache can be set when instantiated the `DataTracker` or
`MailArchive` objects. Alternatively, the following environment variables can be
set:
- `IETFDATA_CACHE_HOST` (defaults to `localhost` when accessing the mail archive)
- `IETFDATA_CACHE_PORT` (defaults to `27017`)
- `IETFDATA_CACHE_USER` (optional)
- `IETFDATA_CACHE_PORT` (optional)

Release Process
---------------

- Edit CHANGELOG.md and ensure up-to-date
- Edit setup.py to ensure the correct version number is present
- Edit pyproject.toml to ensure the correct version number is present
- Edit ietfdata/datatracker.py to fix version number in DataTracker::ua
- Run `make test` to run the test suite. If any tests fail, fix then
  restart the release process
- Commit changes and push to GitHub
- Check that the GitHub Continuous Integration run succeeds, and fix 
  any problems (this runs with a fresh cache, so can sometimes catch
  problems that aren't found by local tests).
- Run `python3 setup.py sdist bdist_wheel` to prepare the package
- Run `python3 -m twine upload dist/*` to upload the package
- Commit the packages files in `dist/*` push to GitHub
- Tag the release in GitHub
