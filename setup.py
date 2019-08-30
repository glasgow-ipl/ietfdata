import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ietfdata",
    version="0.1.0",
    author="Colin Perkins",
    author_email="csp@csperkins.org",
    description="Access the IETF DataTracker and RFC Index",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/csperkins/ietfdata",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)

