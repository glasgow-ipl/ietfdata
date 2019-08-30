ietf-data -- Access the IETF DataTracker and related resources
==============================================================

  Colin Perkins
  https://csperkins.org/

  This project contains Python 3 libraries to interact with, and access, the
  IETF datatracker, RFC index, and related resources.



Getting started
---------------

  The project uses Pipenv for dependency management. To begin, run:
  ```~~~~~~~~
  pipenv install --dev
  ```
  to create a Python virtual environment with appropriate packages install.
  Then, run:
  ```~~~~~~~~
  pipenv shell
  ```
  to start the virtual environment, within which you can run the scripts.

  Once the virtual environment is started, running:
  ```~~~~~~~~
  python3 ietfdata/datatracker.py 
  ```
  will run the test suite for the datatracker module. Running:
  ```~~~~~~~~
  python3 ietfdata/rfcindex.py
  ```
  Will test the rfcindex module.







