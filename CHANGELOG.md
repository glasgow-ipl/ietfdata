Change Log -- ietfdata
======================

## Version 0.4.1 -- ??

 - Update cache support
 - Expand parameters for `person_aliases()`
 - Expand parameters for `people()`
 - Add `person_from_name_email()` to DatatrackerExt
 - Rename `MailingList`-related types and methods in Datatracker to
   `EmailList` to make it easier to use DataTracker and MailArchive
   classes together
 - Add methods and types relating to countries and continents


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


## Version 0.3.1 -- 2020-06-13

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


## Version 0.1.1 -- 2019-08-30

 - Fix license metadata


## Version 0.1.0 -- 2019-08-30

 - Initial release
