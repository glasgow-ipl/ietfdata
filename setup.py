import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="ietfdata",
    version="0.8.1",
    author="Colin Perkins",
    author_email="csp@csperkins.org",
    description="Access the IETF Data Tracker and RFC Index",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/glasgow-ipl/ietfdata",
    packages=setuptools.find_packages(),
    package_data = {
        'ietfdata': ['py.typed'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11',
    setup_requires=["setuptools-pipfile"],
    tests_require=[],
    use_pipfile=True
)
