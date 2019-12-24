ietf-data -- Access the IETF DataTracker and related resources
==============================================================

  Colin Perkins
  https://csperkins.org/

  This project contains Python 3 libraries to interact with, and
  access, the (IETF data tracker)[https://datatracker.ietf.org], 
  (RFC index)[https://www.rfc-editor.org], and related resources.



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



Release Process
---------------

- Edit CHANGELOG.md and ensure up-to-date
- Edit setup.py to ensure the correct version number is present
- Commit changes and push to Github
- Run `make test` to run the test suite. If any tests fail, fix then
  restart the release process
- Run `python3 setup.py sdist bdist_wheel` to prepare the package
- Run `python3 -m twine upload dist/*` to upload the package
- Commit the packages files in `dist/*` push to Github
- Tag the release in Github



