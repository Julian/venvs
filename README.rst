=====
mkenv
=====

mkenv is a simpler tool for creating virtualenvs in a central location.

It consists of the 5% of `virtualenvwrapper
<https://virtualenvwrapper.readthedocs.org/en/latest/>`_ that I actually use.


Installation
------------

The usual::

    $ pip install mkenv


Usage
-----

Usage is similar to ``mkvirtualenv``, although ``mkenv`` passes arguments
directly through to ``virtualenv``::

    $ mkenv nameofvenv -- -p python2.6

will create a virtual environment in an appropriate platform-specific data
directory, or in the directory specified by ``WORKON_HOME`` for compatibility.
