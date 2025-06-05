# The ietfdata library - Access the IETF Datatracker and related resources

This project contains Python 3 libraries to interact with, and
access, the [IETF datatracker](https://datatracker.ietf.org), 
[RFC index](https://www.rfc-editor.org), and related resources.


## Installation

The `ietfdata` library is distributed as a Python package. You
should be able to install via `pip` in the usual manner:

```~~~~~~~~
pip install ietfdata
```

### Development

To modify the `ietfdata` library, clone from GitHub then follow the
following instructions to install dependencies and test the results.
If you just intend to use the library to support writing a paper or 
to perform some other analysis, you can skip this section.

The project uses `pipenv` for dependency management. To begin, run:
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


## Accessing the IETF Datatracker

The `DataTracker` class provides an interface to the IETF Datatracker,
providing metadata about the IETF standards process.

### Instantiation

There are two ways to instantiate this class, depending on how it is to be
used. If the intention is to perform live queries of the Datatracker, for
example as part of a tool that provides an interactive dashboard or status
report, then it should be instantiated using the `DTBackendLive` back end,
as follows:

```~~~~~~~~
dt = DataTracker(DTBackendLive())
```

In this case, the `DataTracker` class will directly query the online IETF
Datatracker for every request you make.

Alternatively, if the intent is to perform analysis of a snapshot of the
data, for example if writing a research paper, a dissertation, or as part
of a student project, then the `DTBackendArchive` should be used:

```~~~~~~~~
dt = DataTracker(DTBackendArchive(sqlite_file="ietfdata.sqlite"))
```

In this case, the `DataTracker` class will create the specified sqlite file
if it doesn't exist and download a complete copy of the data from the IETF
Datatracker (this will take around 24 hours, and will generate an sqlite
file that is around 1.5GB in size; if the download is interrupted, it is
safe to rerun the above operation and the download should resume where it
left-off). Once the sqlite file is downloaded, future instantiations of the
`DataTracker` will read from it directly and will not access the online IETF
Datatracker, making them much faster and avoiding overloading the IETF's
servers.

If you are working on a paper, project, or dissertation with a group of
people, one person should create the `ietfdata.sqlite` file, then share
a copy with the others. This avoids overloading the IETF's servers, and
ensures that everyone working in the group generates the same results.

It is safe to use the same sqlite file with both the `DataTracker` and
`MailArchive3` classes.

### Usage

(tbd)


## Accessing the IETF Mail Archive

The `MailArchive3` class provides an interface to accessing the IETF
email archive.

### Instantiation

(tbd)


It is safe to use the same sqlite file with both the `DataTracker` and
`MailArchive3` classes.


### Usage

(tbd)


## Accessing the RFC Index

(tbd)




## Release Process

- Edit CHANGELOG.md and ensure up-to-date
- Edit setup.py to ensure the correct version number is present
- Edit pyproject.toml to ensure the correct version number is present
- Edit ietfdata/dtbackend.py to ensure the correct version number if
  present (there is one copy in each back-end)
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

