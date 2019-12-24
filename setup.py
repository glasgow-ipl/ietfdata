import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ietfdata",
    version="0.1.5",
    author="Colin Perkins",
    author_email="csp@csperkins.org",
    description="Access the IETF Data Tracker and RFC Index",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/csperkins/ietfdata",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)

