#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Minimal example of the CEFBrowser widget use. Here you don't have any controls
(back / forth / reload) or whatsoever. Just a kivy app displaying the
chromium-webview.
"""


import os
import sys
import time
import threading

from kivy.app import App
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from cefbrowser import CEFBrowser


if __name__ == '__main__':
    # Create CEFBrowser instance. Go to JS binding test-site.
    print "file://"+os.path.join(os.path.dirname(os.path.realpath(__file__)), "general.html")
    cb = CEFBrowser(url="file://"+os.path.join(os.path.dirname(os.path.realpath(__file__)), "general.html"))

    try:
        print(cb._browser.GetDevToolsURL())
    except:
        print("You are not using the GetDevToolsURL extension of cefpython.")
    # cb._browser.ShowDevTools()

    # Define upcall (JS to Python) callback
    def test_result(res, exp, ident, desc, *largs):
        print "callback in Python from JS", exp, ident, desc, largs
        def th(*largs):
            if ident=="focus":
                time.sleep(1)
            elif ident[:11]=="input_type_":
                time.sleep(0.5)
            else:
                time.sleep(0.1)
            if ident=="alert":
                cb.js.result_continue()
                CEFBrowser._js_alert.js_continue(True, "")
                CEFBrowser._js_alert.dismiss()
                return
            elif ident=="confirm_yes":
                cb.js.result_continue()
                CEFBrowser._js_confirm.js_continue(True, "")
                CEFBrowser._js_confirm.dismiss()
                return
            elif ident=="confirm_no":
                cb.js.result_continue()
                CEFBrowser._js_confirm.js_continue(False, "")
                CEFBrowser._js_confirm.dismiss()
                return
            elif ident=="prompt":
                cb.js.result_continue()
                CEFBrowser._js_prompt.js_continue(True, "Test")
                CEFBrowser._js_prompt.dismiss()
                return
            cb.js.result_continue()
        threading.Thread(target=th).start()
    cb.js.bind(test_result=test_result)

    # Start the kivy App
    class SimpleBrowserApp(App):
        def build(self):
            return cb
            # http://demo.redminecrm.com/projects/agile/agile/board

    SimpleBrowserApp().run()
