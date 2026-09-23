# The ietfdata library - Access the IETF Datatracker and related resources

This project contains Python 3 libraries to retrieve and work with data
from the [IETF Datatracker](https://datatracker.ietf.org), [IETF Mail
Archive](https://mailarchive.ietf.org), [RFC
index](https://www.rfc-editor.org), and related resources.


## Installation

The `ietfdata` library is distributed as a Python package. You
should be able to install via `pip` in the usual manner:
```sh
pip install ietfdata
```

## Accessing the IETF Datatracker

The `DataTracker` class provides an interface for programmatic access to
the IETF Datatracker, providing metadata about the development of IETF
standards.

### Instantiation

There are two ways to instantiate this class, depending on how it is to be
used. The normal way, when writing code to perform analysis of a snapshot
of the IETF data, for example if writing a research paper, a dissertation,
or as part of a student project, is to use an archive file:
``` python
dt = DataTracker(DTBackendArchive("archive/ietf-dt.sqlite"))
```
When instantiated in this manner, the `DataTracker` class will read from
the specified `sqlite` database.

If the specified `sqlite` database does not exist, then the `DataTracker`
class will fetch a complete copy of the data from the IETF Datatracker.
This will take around 24 hours, and will produce database that is about
2GB in size (if interrupted, it is safe to rerun the above operation and
the download will resume where it left-off).  Once the `sqlite` database
is downloaded, future instantiations of the `DataTracker` will read from it
directly and will not access the online IETF Datatracker, making them much
faster and avoiding overloading the IETF's servers.

The following can be run from the command line to fetch a copy of the
database:
``` bash
  python3 -m ietfdata.tools.download_dt archive/ietf-dt.sqlite
```
If you are working on a paper, project, or dissertation with a group of
people, one person should create the `sqlite` database and share a copy
with the others. This avoids overloading the IETF's servers, and ensures
that everyone working in the group generates the same results.



Alternatively, when writing code to perform live queries of the IETF
Datatracker, for example as part of a tool that provides an interactive
dashboard or status report, the `DataTracker` should be instantiated as
follows:
```python
dt = DataTracker(DTBackendLive())
```
In this case, the `DataTracker` class will directly query the online IETF
Datatracker for every request you make. This is appropriate when making
small numbers of queries, for exploratory programming or when performing
a live status check, but must not be used for tasks that need to make
large numbers of queries. The IETF will block your access if you make
many queries using `DTBackendLive()`.



### Usage

The `DataTracker` provides an extensive API that is best explored by
reading the source code for `datatracker.py` and `datatracker_types.py`.
The `examples/` directory contains a number of examples of how to use 
the library.

Start by importing and instantiating the library:
```python
from ietfdata.datatracker import *
dt = DataTracker(DTBackendArchive("archive/ietf-dt.sqlite"))
```

To find information about a person:
```python
p = dt.person_from_email("csp@csperkins.org")
print(p.name)
print(p.biography)
```

To find information about a document:
```python
d = dt.document_from_rfc("RFC9000")
print(d.title)
print(d.group)
```

To find information about a group:
```python
g = dt.group(d.group)
print(g.acronym)

for e in dt.group_events(group = g):
  print(e.time)
  print(e.desc)
```

There is a lot of information in the Datatracker. Read the source code
the `datatracker.py` to understand what functions can be called, and the
code for `datatracker_types.py` to understand the objects the take or
return.


## Accessing the IETF Datatracker Extensions

The `DataTrackerExt` class is a subclass of `DataTracker` that provides
additional features on top of those provided by the IETF Datatracker.

### Instantiation
The `DataTrackerExt` class is instantiated in an analogous manner to the
`DataTracker` class:
``` python
from ietfdata.datatracker_ext import *

dt = DataTrackerExt(DTBackendArchive("archive/ietf-dt.sqlite"))
```
Since it's a subclass of the `DataTracker`, any of the methods that can be
used on the `DataTracker` can also be used with `DataTrackerExt`.

The `DataTrackerExt` offers a number of other useful features including
the ability to find the history of a draft or RFC:
```python
from ietfdata.datatracker_ext import *
from ietfdata.rfcindex        import *

dte = DataTrackerExt(DTBackendArchive("archive/ietfdata-dt.sqlite"))
ri  = RFCIndex(rfc_index="archive/rfc-index.xml")
rfc = ri.rfc("RFC9000")
for d in dte.draft_history_for_rfc(rfc):
    print("    {0: <50} | {1} | {2}".format(d.draft.name, d.rev, d.date.strftime("%Y-%m-%d")))
```
or the history of an Internet-draft:
```python
dte = DataTrackerExt(DTBackendArchive("archive/ietfdata-dt.sqlite"))
doc = dt.document_from_draft("draft-ietf-avtcore-ecn-for-rtp")
for d in dte.draft_history(doc):
    print("    {0: <50} | {1} | {2}".format(d.draft.name, d.rev, d.date.strftime("%Y-%m-%d")))
```

It also contains methods to find the people who currently hold various
leadership roles in the IETF, IRTF, and IAB, and the set of currently
active working groups and research groups, for example:
```python
for p in dte.working_group_chairs():
    print(p.name)
```
Finally, the `DataTrackerExt` class contains a method that given a name and
an email address, for example as might be extracted from an email "From:"
header, tries to find a person in the DataTracker. This uses a number of
heuristics to find the right person even if there is no exact match:
```python
p1 = dte.person_from_name_email("Colin Perkins", "csp@csperkins.org")
print(p1.id)
p2 = dte.person_from_name_email("Colin Perkins via Datatracker", "noreply@ietf.org")
print(p2.id)
```


## Accessing the IETF Mail Archive

The `MailArchive3` class provides an interface to accessing the IETF
email archive.

### Instantiation

The `MailArchive3` class is instantiated as follows, giving a path to
an `sqlite` database containing a copy of the archive:
```python
ma = MailArchive("archive/ietf-ma.sqlite")
```
Once instantiated, a call to `ma.update()` will bring the `sqlite`
database up to date with the IETF mail archive. The first time the
`ma.update()` function is called, it will download a complete copy of the
mail archive. This is approximately 40 gigabytes in size and will take
around 24 hours to download. Subsequent calls only fetch new messages,
and are much faster.

The following can be run from the command line to fetch a copy of the
mail archive:
``` bash
  python3 -m ietfdata.tools.download_ma_ietf archive/ietf-ma.sqlite
```
If you are working on a paper, project, or dissertation with a group of
people, one person should create the `sqlite` database and share a copy
with the others. This avoids overloading the IETF's servers, and ensures
that everyone working in the group generates the same results.



### Usage

Start by importing and instantiating the library:
```python
from ietfdata.mailarchive3 import *
ma = MailArchive("archive/ietf-ma.sqlite")
```
Once this is done, you can find the mailing list names:
```python
for ml_name in ma.mailing_list_names()
  print(ml_name)
```

You can find information about a particular mailing list:
```python3
ml = ma.mailing_list("quic")
print(ml.num_messages())
```

You can find information about the messages:
```python3
for msg in ml.messages():
  print(f"From:    {msg.from_()}")
  print(f"To:      {msg.to()}")
  print(f"Subject: {msg.subject()}")
  print("")
```

Read the source code for `mailarchive3.py` for details.


## Accessing the RFC Index

(tbd)

See `rfcindex.py`



## Development

To modify the `ietfdata` library, clone from GitHub then follow the
instructions below to install dependencies and test the results. If you
just intend to use the library to support writing a paper or to perform
some other analysis, you can skip this section.

Create a virtual environment and install dependencies in the usual manner:
```sh
python3 -m venv venv/
source venv/bin/activate
python3 -m pip install -e .
```
Once the virtual environment is started, running:
```sh
python3 tests/test_datatracker.py 
```
will run the test suite for the datatracker module. Running:
```sh
python3 tests/test_rfcindex.py
```
Will test the rfcindex module.



## Release Process

- Edit CHANGELOG.md and ensure up-to-date
- Edit setup.py to ensure the correct version number is present
- Edit pyproject.toml to ensure the correct version number is present
- Edit `ietfdata/dt_backend.py` to ensure the correct version number
- Edit `ietfdata/github.py` to ensure the correct version number
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

