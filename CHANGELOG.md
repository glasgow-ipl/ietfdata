Change Log -- ietfdata
======================

## Version 0.9.0

- Introduce `mailarchive3.py`. This is intended to be an almost
  drop-in replacement for `mailarchive2.py`, that uses a local
  sqlite3 file as the database rather than MongoDB. Currently
  work in progress.
- Update the DataTracker class to support different back ends.
  The `DTBackendLive` class is intended for interactive use, while
  `DTBackendArchive` is intended to support offline use, backed by
  an sqlite file, when preparing a paper, dissertation, or student
  project.


## Version 0.8.3

 - Fix parsing of `Submission` objections that lack a draft
 - Add `ietfdata.tools.organisations.py` as a tool to find
   organisations with which IETF participants may be affiliated.
 - Update tests and examples


## Version 0.8.2

 - Require Python 3.13
 - Update tests and examples
 - Update rate limiting to handle 429 with "Retry-After: 0"


## Version 0.8.1 

 - Fix type mismatch in `DataTrackerExt::draft_history()`


## Version 0.8.0 

 - Use a local sqlite file for the datatracker cache rather than MongoDB.
   The `IETFDATA_CACHEDIR` environment variable specifies the location of
   the cache, defaulting to the current directory if not specified.
   At present, the mailarchive still uses MongoDB.
 - Allow use of local `rfc-index.xml`


## Version 0.7.2 -- 23 August 2024

 - Catch-up with changes to datatracker and RFC Index


## Version 0.7.1 -- 21 May 2024

 - Update dependencies
 - Update tests to catch-up with the datatracker
 - Fix message threading to handle email with no Message-Id header
 - Create index on `in-reply-to` header to improve performance


## Version 0.7.0 -- 19 April 2024

 - Require Python 3.11 or newer
 - Replace Pavlova with Pydantic as the response parser, enabling use
   of recent Python versions. As a result:
    - Python data classes are replaced with Pydantic BaseClass instances.
    - In `Person` and `HistoricalPerson`, the `user, `photo`,
      `photo_thumb`, and `pronouns_freetext` fields change from
      `str` to `Optional[str]`.
    - In `Submission`, the `document_date` and `submission_date` fields
      changes from `datetime` to `date`
    - In `Meeting`, the `date` field changes from `datetime` to `date`
 - Update mailarchive2.py as the new mail access API
 - Remove mailarchive.py
 - Add the following methods, and associated types, to `DataTracker`
     `person_ext_resource()`
     `person_ext_resources()`
     `ext_resource_name()`
     `ext_resource_name_from_slug()`
     `ext_resource_names()`
     `ext_resource_type_name()`
     `ext_resource_type_name_from_slug()`
     `ext_resource_type_names()`
   These make it possible to retrieve GitHub identifiers, and similar,
   for people.
 - Catch-up with changes to the IETF Datatracker:
    - RFCs are now first class documents in the datatracker
    - The type of `Document.rfc` changes to `Optional[str]` and a new
     `Document.rfc_number` field is added with type `Optional[int]`
    - The `DocumentAlias` and `DocumentAliasURI` types are removed; their
      uses are replaced by `Document` and `DocumentURI`
    - The `document_alias()` and `document_aliases()` methods are removed. 
    - Remove `email_list()`, `email_lists()` and `email_list_subscriptions()`


## Version 0.6.8 -- 17 August 2023

 - Catch-up with changes to the Datatracker


## Version 0.6.7 -- 21 June 2023

 - Catch-up with changes to the Datatracker
 - Add threading to mailarchive2


## Version 0.6.6 -- 19 May 2023

 - Catch-up with changes to the Datatracker


## Version 0.6.5 -- 14 December 2022

 - Add `state` filter to `documents()`
 - Update tests


## Version 0.6.4 -- 14 December 2022

 - Fix `meeting_session_status()`


## Version 0.6.3 -- 14 December 2022

 - `meeting_session_status()` can return None
 - Update dependencies to fix security issues


## Version 0.6.2 -- 28 October 2022

 - Catch-up with changes to the Datatracker


## Version 0.6.1 -- 4 August 2022

 - Rename `Message` to `DTMessage`
 - Remove `first_two_lines` from `Submission`, to match changes to the
   datatracker
 - Add `checkedin` field to `MeetingRegistration`


## Version 0.6.0 -- 14 June 2022

 - Switch to requests-cache for the cache


## Version 0.5.7 -- 21 February 2022

 - Fix tests


## Version 0.5.6 -- 21 February 2022

 - Fix `RfcEntry::content_url()` for RFCs 1-999
 - Add `purpose` field to `Session` class, bump cache version


## Version 0.5.5 -- 1 December 2021

 - Be more robust downloading mail archives


## Version 0.5.4 -- 26 November 2021

 - Fix bluesheet document URLs

## Version 0.5.3 -- 22 November 2021

 - Fix potential IMAP timeout
 - Add `on_agenda` field to `Session` class, bump cache version


## Version 0.5.2 -- 26 October 2021

 - Drop required Python version down to 3.8


## Version 0.5.1 -- 1 October 2021

 - Allow empty event type when fetching document events


## Version 0.5.0 -- 19 September 2021

 - Update cache support
 - Expand parameters for `person_aliases()`
 - Expand parameters for `people()`
 - Add `person_from_name_email()` to DatatrackerExt
 - Rename `MailingList`-related types and methods in Datatracker to
   `EmailList` to make it easier to use DataTracker and MailArchive
   classes together
 - Add methods and types relating to countries and continents
 - Update mail archive support


## Version 0.4.0 -- 2021-03-02

 - Add support for caching `Datatracker` requests using MongoDB
 - Add support for accessing the IETF mail archive
 - Expand Datatracker API coverage


## Version 0.3.3 -- 2020-06-28

 - Update `group_histories()` to take a `group` parameter
 - Update `Meeting` to note that the `schedule` is optional
 - Update tests


## Version 0.3.2 -- 2020-06-21

 - Expand API coverage for meeting registrations
 - Update tests


## Version 0.3.1 -- 2020-06-13

 - Expand API coverage for Meetings and IPR disclosures
 - Include the PEP 561 `py.typed` marker in the generated package

## Version 0.3.0 -- 2020-06-07

 - Add `DataTrackerExt` helper class
 - Add API coverage for reviews and IPR disclosures
 - Update Submission class to use `datetime` objects where appropriate


## Version 0.2.0 -- 2020-05-17

 - Greatly expand Datatracker API coverage
 - Updated methods to use URI subtypes rather than strings
 - Updated method and parameter names for consistency
 - Add experimental support for caching requests


## Version 0.1.5 -- 2019-12-24

 - Add Meeting::status() method


## Version 0.1.4 -- 2019-10-07

 - Update tests


## Version 0.1.3 -- 2019-09-16

 - Work around problems with Datatracker dropping connections when
   HTTP connection reuse is active
 - Catch-up with changes to Datatracker API
 - Catch-up with changes to RFC index format


## Version 0.1.2 -- 2019-09-09

 - Catch-up with Datatracker Version 6.101.0. This added IANA expert review
   tracking, with additional states.


## Version 0.1.1 -- 2019-08-30

 - Fix license metadata


## Version 0.1.0 -- 2019-08-30

 - Initial release
