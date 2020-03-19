Change Log -- ietfdata
======================

## v0.2.0 -- ???

 - Update documentation of RfcEntry class
 - Update tests
 - Introduce and use URI types throughout
 - Re-enable HTTP connection reuse
 - Add `Datatracker::emails()` method
 - Add `Datatracker::document_states()` method
 - Add `Datatracker::meeting()` method
 - Update `Datatracker::meetings()` to take `start_date` and `end_date`
   parameters rather than `since` and `until`.
 - Add `Datatracker::meeting_schedule()` method 
 - Add `Datatracker::Schedule` type
 - Add `Datatracker::Timeslot` type
 - Add `Datatracker::Assignment` type


## v0.1.5 -- 2019-12-24

 - Add Meeting::status() method


## v0.1.4 -- 2019-10-07

 - Update tests


## v0.1.3 -- 2019-09-16

 - Work around problems with Datatracker dropping connections when
   HTTP connection reuse is active
 - Catch-up with changes to Datatracker API
 - Catch-up with changes to RFC index format


## v0.1.2 -- 2019-09-09

 - Catch-up with Datatracker v6.101.0. This added IANA expert review
   tracking, with additional states.


## v0.1.1 -- 2019-08-30

 - Fix license metadata


## v0.1.0 -- 2019-08-30

 - Initial release
