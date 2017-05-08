#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Example of the CEFBrowser widget communicating to JavaScript in its Browser.
"""


from kivy.app import App
from kivy.garden.cefpython import CEFBrowser


if __name__ == '__main__':
    # Create CEFBrowser instance. Go to JS binding test-site.
    cb = CEFBrowser(url="http://jegger.ch/datapool/app/test_js_bind.html")

    # Define upcall (JS to Python) callback
    def callback(*largs):
        print("callback in Python from JS", largs)
    cb.js.bind(test_upcall=callback)

    # Do the downcall (Python to JS) as soon as site is loaded.
    # The downcall will trigger the upcall on the test-site.
    def do_downcall(*largs):
        cb.js.test_downcall("test", 3)
    cb.bind(on_load_end=do_downcall)

    # Start the kivy App
    class JSBindBrowserApp(App):
        def build(self):
            return cb
    JSBindBrowserApp().run()
