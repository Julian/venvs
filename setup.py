import os

from setuptools import find_packages, setup

from mkenv import __version__


with open(os.path.join(os.path.dirname(__file__), "README.rst")) as readme:
    long_description = readme.read()

classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy"
]

setup(
    name="mkenv",
    py_modules=["mkenv"],
    version=__version__,
    entry_points={
        "console_scripts": ["mkenv = mkenv:main", "mkvenv = mkenv:main"],
    },
    install_requires=["appdirs"],
    author="Julian Berman",
    author_email="Julian@GrayVines.com",
    classifiers=classifiers,
    description="A simpler tool for creating venvs in a central location",
    license="MIT",
    long_description=long_description,
    url="https://github.com/Julian/mkenv",
)
