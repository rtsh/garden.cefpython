#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from .cefbrowser import CEFBrowser  # noqa: F401
from .version import __version__  # noqa: F401
import os


cef_test_url = "file://" + os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    "test.html",
)
