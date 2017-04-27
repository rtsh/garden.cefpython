#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Minimal example of the CEFBrowser widget use. Here you don't have any controls
(back / forth / reload) or whatsoever. Just a kivy app displaying the
chromium-webview.
"""


import os
import time
import threading

from kivy.app import App
from kivy.garden.cefpython import CEFBrowser


if __name__ == '__main__':
    CEFBrowser.update_flags({'enable-copy-paste': True, 'enable-fps': True})
    # Create CEFBrowser instance. Go to JS binding test-site.
    print("file://" + os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "general.html",
    ))
    cb = CEFBrowser(
        url="file://" + os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "general.html",
        ),
    )

    try:
        from http.server import BaseHTTPRequestHandler, HTTPServer
    except:
        from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            file_path_components = self.path.split('/')
            try:
                file_path_components[-1] = file_path_components[-1][
                    :file_path_components[-1].index('?')]
            except:
                pass
            file_path = os.path.join(
                os.path.dirname(os.path.realpath(__file__)),
                'data',
                *file_path_components,
            )
            if not os.path.isfile(file_path):
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(open(file_path, 'rb').read())
    httpd = HTTPServer(('', 8081), RequestHandler)
    threading.Thread(target=httpd.serve_forever, args=()).start()

    print("http://localhost:8081/general.html")
    cb = CEFBrowser(url="http://localhost:8081/general.html")

    # cb._browser.ShowDevTools()

    def _test_result(res, exp, ident, desc):
        if ident == "focus":
            time.sleep(1)
        elif ident[:11] == "input_type_":
            time.sleep(0.5)
        else:
            time.sleep(0.1)
        if ident == "alert":
            cb.js.result_continue()
            CEFBrowser._js_alert.js_continue(True, "")
            CEFBrowser._js_alert.dismiss()
            return
        elif ident == "confirm_yes":
            cb.js.result_continue()
            CEFBrowser._js_confirm.js_continue(True, "")
            CEFBrowser._js_confirm.dismiss()
            return
        elif ident == "confirm_no":
            cb.js.result_continue()
            CEFBrowser._js_confirm.js_continue(False, "")
            CEFBrowser._js_confirm.dismiss()
            return
        elif ident == "prompt":
            cb.js.result_continue()
            CEFBrowser._js_prompt.js_continue(True, "Test")
            CEFBrowser._js_prompt.dismiss()
            return
        cb.js.result_continue()

    # Define upcall (JS to Python) callback
    def test_result(res, exp, ident, desc, *largs):
        print("callback in Python from JS", exp, ident, desc, largs)
        threading.Thread(
            target=_test_result,
            args=(res, exp, ident, desc),
        ).start()

    cb.js.bind(test_result=test_result)

    # Start the kivy App
    class SimpleBrowserApp(App):
        def build(self):
            return cb
            # http://demo.redminecrm.com/projects/agile/agile/board

        def on_stop(self, *largs):
            httpd.shutdown()

    SimpleBrowserApp().run()
