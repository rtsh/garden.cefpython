#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Minimal example of the CEFBrowser widget use. Here you don't have any controls
(back / forth / reload) or whatsoever. Just a kivy app displaying the
chromium-webview.
In this example we demonstrate how the cache path of CEF can be set.
"""


import os

from kivy.app import App
from kivy.garden.cefpython import CEFBrowser
from kivy.logger import Logger
from kivy.uix.label import Label


if __name__ == '__main__':
    class SimpleBrowserApp(App):
        def build(self):
            CEFBrowser.set_data_path(os.path.realpath("./cef_data"))
            Logger.info("Example: The CEF pathes have been set to \n- Cache %s\n- Cookies %s\n- Logs %s", CEFBrowser._caches_path, CEFBrowser._cookies_path, CEFBrowser._logs_path)
            cb = CEFBrowser(url="http://jegger.ch/datapool/app/test.html")
            return cb

    SimpleBrowserApp().run()
