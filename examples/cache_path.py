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
            CEFBrowser.cache_path = os.path.realpath("./cef_cache")
            if not os.path.isdir(CEFBrowser.cache_path):
                try:
                    os.mkdir(CEFBrowser.cache_path, 0o0777)
                except Exception as err:
                    Logger.error("Example: Could not create CEF cache directory: %s", err)
                    return Label(text="[color=ff0000][b]Could not create CEF cache directory[/b][/color]\n\n%s\n\n- You need to run this script from a directory where you have write permission.\n- A file with the name 'cef_cache' must not exist in that directory."%(err,), markup=True)
            Logger.info("Example: The CEF cache path has been set to: %s", CEFBrowser.cache_path)
            cb = CEFBrowser(url="http://rentouch.ch")
            return cb

    SimpleBrowserApp().run()
    cefpython.Shutdown()

