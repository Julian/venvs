from setuptools import setup

import os
import shutil

src = os.path.join(os.path.dirname(__file__), 'requirements.txt')
dst = os.path.join(os.path.dirname(__file__), 'venvs')
shutil.copy(src, dst)

setup(use_scm_version=True)
