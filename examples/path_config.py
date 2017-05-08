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


if __name__ == '__main__':
    class SimpleBrowserApp(App):
        def build(self):
            # Set runtime data paths
            CEFBrowser.set_data_path(os.path.realpath("./cef_data"))
            # CEFBrowser.set_caches_path(os.path.realpath("./cef_caches"))
            # CEFBrowser.set_cookies_path(os.path.realpath("./cef_cookies"))
            # CEFBrowser.set_logs_path(os.path.realpath("./cef_logs"))
            Logger.info("Example: The CEF pathes have been set to")
            Logger.info("- Cache %s", CEFBrowser._caches_path)
            Logger.info("- Cookies %s", CEFBrowser._cookies_path)
            Logger.info("- Logs %s", CEFBrowser._logs_path)

            # Create CEFBrowser instance. Go to test-site.
            cb = CEFBrowser(url="http://jegger.ch/datapool/app/test.html")
            return cb

    SimpleBrowserApp().run()
