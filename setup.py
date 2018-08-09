import os

from setuptools import find_packages, setup


with open(os.path.join(os.path.dirname(__file__), "README.rst")) as readme:
    long_description = readme.read()

classifiers = [
    "Development Status :: 3 - Alpha",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: 2",
    "Programming Language :: Python :: 3.4",
    "Programming Language :: Python :: 3.5",
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: Implementation :: CPython",
    "Programming Language :: Python :: Implementation :: PyPy",
]

setup(
    name="mkenv",
    url="https://github.com/Julian/mkenv",

    description="A simpler tool for creating venvs in a central location",
    long_description=long_description,

    author="Julian Berman",
    author_email="Julian@GrayVines.com",

    classifiers=classifiers,
    license="MIT",

    packages=find_packages(),

    setup_requires=["setuptools_scm"],
    use_scm_version=True,

    install_requires=[
        "appdirs",
        "attrs",
        "click",
        "filesystems",
        "packaging",
        "pytoml>=0.1.16",
        "tqdm",
        "virtualenv",
    ],
    entry_points={
        "console_scripts": [
            "mkenv = mkenv.make:main",
            "convergeenvs = mkenv.converge:main",
            "findenv = mkenv.find:main",
            "rmenv = mkenv.remove:main",
        ],
    },
)
