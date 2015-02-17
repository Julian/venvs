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

Usage is similar to ``mkvirtualenv``, although ``mkenv`` passes
arguments directly through to ``virtualenv``::

    $ mkenv nameofvenv -- -p pypy

will create a virtual environment in an appropriate platform-specific
data directory, or in the directory specified by ``WORKON_HOME`` for
compatibility.


Why don't I use virtualenvwrapper?
----------------------------------

``virtualenvwrapper`` is great! I've used it for a few years. But I've
slowly settled on a much smaller subset of its functionality that I like
to use. Specifically:

    * I don't like activating virtualenvs.
      
      virtualenvs are magical and hacky enough on their own, and piling
      activation on top just makes things even more messy, especially
      if you're moving around between different projects in a shell.
      Some people use ``cd`` tricks to solve this, but I just want
      simiplicity.

    * I don't need project support.

      I've never attached a project to a virtualenv. I just use a naming
      convention, naming the virtualenv with the name of the repo (with simple
      coersion), and then using `dynamic directory expansion in my shell
      <https://github.com/Julian/dotfiles/blob/51bb47e/.config/zsh/.zshrc#L57-L80>`_
      to handle association.

Basically, I just want a thing that is managing a central repository of
virtualenvs for me. So that's what ``mkenv`` does!
