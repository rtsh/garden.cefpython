#!/usr/bin/env python
# -*- coding: UTF-8 -*-

__all__ = ('cef_test_url', 'CEFBrowser', )

import os

from cefbrowser import CEFBrowser

cef_test_url = "file://"+os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.html")
