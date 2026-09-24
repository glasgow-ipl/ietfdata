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

> [!CAUTION]
> This section is incomplete. Pull requests to provide examples for
> how to perform common tasks are welcomed.

The `DataTracker` provides an extensive API that is best explored by
reading the source code for `datatracker.py` and `datatracker_types.py`.
The `examples/` directory contains a number of examples of how to use 
the library.

Start by importing and instantiating the library:
```python
from ietfdata.datatracker import *

dt = DataTracker(DTBackendArchive("archive/ietf-dt.sqlite"))
```
Then follow the suggestions below, and read the relevant sections
of the `datatracker.py` source code, for examples of how to access
the data.

#### People

To find information about a person:
```python
p = dt.person_from_email("csp@csperkins.org")
print(p.name)
print(p.biography)
```

#### Documents

To find information about a document:
```python
d = dt.document_from_rfc("RFC9000")
print(d.name)
print(d.title)
print(d.abstract)
print(d.group)       # WG or RG name, if any
print(d.stream)      # IETF, IRTF, etc.
print(d.rfc)         # Returns a string
print(d.rfc_number)  # Returns an integer
print(d.rev)         # If an Internet-draft, returns the draft revision
print(d.ad)          # Responsible area director, if any
print(d.shepheard)   # Document shepherd, if any
print(d.states)      # Use with `dt.document_state()`
print(d.submissions) # Use with `dt.submissions()`
print(d.time)
```

Warning: the `d.time` field is the time of the last event relating to the
document (see `dt.document_events()` below), not the time when the latest
version of the document was published. To find the date when an
Internet-Draft was last modified, look at `d.submissions`; to find the
date of RFC publication look at `dt.document_events()` and find the event
with type `published_rfc`.

The value returned by `d.group` can be passed to `dt.group()` (see below)
to find information about the working group, research group, or area that
owns the document.

The value returned by `d.ad` and `d.shepherd` can be passed to `dt.person()`

The value returned by `d.submissions` is a list of the different versions
of the document:
```python
d = dt.document_from_draft("draft-ietf-taps-interface")
for s in d.submissions:
    submission = dt.submission(s)
    print(submission.name)
    print(submission.rev)
    print(submission.document_date)
    print(submission.submission_date)
    print(submission.draft)
    print(submission.group)
    print(submission.replaces)
    print(submission.authors)
    print(submission.title)
    print(submission.abstract)
    print(submission.state)
    print("")
```

It's possible to find documents that a document, `d`, relates to (these are
usually the normative and informative references included in the document):
```python
for rel_doc in dt.related_documents(source = d):
    print(rel_doc.relationship, rel_doc.target)
```
The return values `rel_doc.target` can be passed to `dt.document()` to find
information about the target document.

Similarly, documents that relate to a document can be found:
```python
for r in dt.related_documents(target = d):
    print(r.relationship, r.source)
```
This can be used to find documents that reference the document `d`.

A useful query is:
```python
d = dt.document_from_rfc("RFC9622")
for r in dt.related_documents(target = d, relationship_type_slug="became_rfc"):
    print(r.relationship, r.source)
```
which finds the Internet-draft that became the specified RFC.

The complete history of a single document can be found via:
```python
for event in dt.document_events(d):
    print(event)
```

The authors of a document can be found using the `dt.document_authors()`
method. Documents written by a particular person can be found using
the methods `dt.documents_authored_by_person()` and `dt.documents_authored_by_email()`.

See also the discussion of Datatracker Extensions below.


#### Groups

To find information about a group:
```python
d = dt.document_from_rfc("RFC9000")
g = dt.group(d.group)
print(g.acronym)

for e in dt.group_events(group = g):
  print(e.time)
  print(e.desc)
```

#### Meetings

(tbd)


#### Intellectual Property Rights Disclosures

(tbd)



## Accessing the IETF Datatracker Extensions

The `DataTrackerExt` class is a subclass of `DataTracker` that provides
additional features on top of those provided by the IETF Datatracker.

### Instantiation
The `DataTrackerExt` class is instantiated in an analogous manner to the
`DataTracker` class:
``` python
from ietfdata.datatracker_ext import *

dte = DataTrackerExt(DTBackendArchive("archive/ietf-dt.sqlite"))
```

### Usage
Since it's a subclass of the `DataTracker`, any of the methods that can be
used on the `DataTracker` can also be used with `DataTrackerExt`.

The `DataTrackerExt` offers a number of other useful features including
the ability to find the history of an RFC:
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
c = dte.ietf_chair()
print(c.name)

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
from ietfdata.mailarchive3 import *
ma = MailArchive("archive/ietf-ma.sqlite")
```
If the specified `sqlite` database does not exist, the `ma.update()` method
can be called to download a complete copy of the mail archive and store it
in the database. The mail archive is approximately 40 gigabytes in size and
will take around 24 hours to download. If the `sqlite` database file already
exists, calling `ma.update()` will only fetch new messages, and so will be
much faster. 

The following can be run from the command line to fetch a copy of the
mail archive and create the `sqlite` database:
``` bash
  python3 -m ietfdata.tools.download_ma_ietf archive/ietf-ma.sqlite
```
If you are working on a paper, project, or dissertation with a group of
people, one person should create the `sqlite` database and share a copy
with the others. This avoids overloading the IETF's servers, and ensures
that everyone working in the group generates the same results.


### Usage

Once you have a copy of the `sqlite` database containing the mail archive,
start by importing and instantiating the library:
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
Each mailing list is represented by a `MailingList` object. That has a
`messages()` method to retrieve the messages, and a `threads()` method
to retrieve all discussion threads.


You can find information about the messages sent to a mailing list:
```python3
ml = ma.mailing_list("quic")
for envelope in ml.messages():
  print(f"From:    {envelope.from_()}")
  print(f"To:      {envelope.to()}")
  print(f"Subject: {envelope.subject()}")
  print(f"Date:    {envelope.date()}")
  print(f"Message-Id:  {envelope.message_id()}")
  print("")
```
Each email message is represented by an `Envelope` object. The envelope has
methods (`from_()`, `to()`, `subject()`, etc.) to access the header fields,
a `contents()` method to retrieve the message contents, and `replies()`
and `in_reply_to()` methods to follow the thread of discussion.

Each email message on the server is uniquely identified by the combination
of the name of the mailing list it was sent to, and the `uidvalidity()` and
`uid()` fields of the message. Each message also has a `message_id()` that
identifies the message.

If a message is sent copied to several different mailing lists, then it
will appear in the mail archive several times, one copy in each mailing
list. Each copy will have a different mailing list, `uidvalidity()` and
`uid()`, but all will have the same `message_id()`.


Read the source code for `mailarchive3.py` for details.


## Accessing the RFC Index

(tbd)

See `rfcindex.py`


## Entity Resolution

One of the challenges in working with the IETF data is determining whether
different names or identifiers represent the same person or organisation
(this is known as "entity resolution"). For example, the email addresses
`csp@csperkins.org`, `colin.perkins@glasgow.ac.uk`, `csp@isi.edu`, and
`c.perkins@cs.ucl.ac.uk` all represent the same person, but working in
different jobs at different stages of their career. Similarly, "Technische
Universität München", "TU Munich", and "TU Muenchen" all represent the same
university.

The `ietfdata` library contains code that (attempts to) perform entity
resolution. This can be run from the command lines as follows:
```sh
python3 -m ietfdata.tools.participants archive/ietf-dt.sqlite archive/ietf-ma.sqlite participants.json

python3 -m ietfdata.tools.organisations archive/ietf-dt.sqlite archive/rfc-index.xml organisations.json

python3 -m ietfdata.tools.affiliations archive/ietf-dt.sqlite archive/rfc-index.xml participants.json organisations.json affiliations.json
```
Running these commands will generate three files:

* The file `participants.json` contains information about the people,
  giving each participant in IETF a unique identifier (e.g., `PID:063009`)
  that is associated with their names, email addresses, DataTracker
  identifier, GitHub username, any other identifying information that can be
  extracted.

* The file `organisations.json` contains information about organisations,
  giving each a unique identifier (e.g., `ORG:001156`) that's associated
  with the different names the organisation has been given and the domain
  names it uses.

* The file `affiliations.json`, matches participants to organisations at
  different stages of their career.

As of September 2026, the entity resolution code runs but has known
problems and limitations that mean the results are not always accurate.


## GitHub Access

IETF working groups increasing make use of GitHub to prepare documents.
The `ietfdata` library contains minimal, extremely limited, code to fetch
relevant data from GitHub:
```python
from ietfdata.github import GitHub

gh = GitHub()
for issue in gh.issues("quicwg", "base-drafts"):
    print(issue)

for comment in gh.comments_for_issue("quicwg", "base-drafts", "5010"):
    print(comment)

user = gh.user("csperkins")
print(user)

for repo in gh.repos_for_user("csperkins"):
    print(repo)
```

NOTE: GitHub aggressively rate limits access for unauthenticated users to
60 requests per hour.  Set the environment variable `GITHUB_API_TOKEN` to
your GitHub access token before using this code to receive the higher rate
limit (5000 requests per hour) available to logged-in GitHub users. If you
don't have a GitHub access token, see `https://github.com/settings/tokens` when
logged in to GitHub and select "Generate new token".



## Development

To modify the `ietfdata` library, clone from GitHub then follow the
instructions below to install dependencies and test the results. If you
just intend to use the library to support writing a paper, as part of a
student project, or to perform some other analysis, you can skip the
remainder of this document.

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
- Edit pyproject.toml to ensure the correct version number is present
- Edit `ietfdata/dt_backend.py` to ensure the correct version number
- Edit `ietfdata/github.py` to ensure the correct version number
- Run `make test` to run the test suite. If any tests fail, fix then
  restart the release process
- Commit changes and push to GitHub
- Check that the GitHub Continuous Integration run succeeds, and fix 
  any problems (this runs with a fresh cache, so can sometimes catch
  problems that aren't found by local tests).
- Run `python3 -m build --sdist` to prepare the source package
- Run `python3 -m build --wheel` to prepare the binary package
- Run `python3 -m twine upload dist/*` to upload the packages
- Commit the packages files in `dist/*` push to GitHub
- Tag the release in GitHub

