#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Minimal example of the CEFBrowser widget use. Here you don't have any controls
(back / forth / reload) or whatsoever. Just a kivy app displaying the
chromium-webview.
"""


from kivy.app import App
from kivy.garden.cefpython import CEFBrowser


if __name__ == '__main__':
    class SimpleBrowserApp(App):
        def build(self):
            cb = CEFBrowser(url="https://self-signed.badssl.com")
            def my_cert_handler(browser, err, url):
                """
                Here, we have the policy to only accept invalid certificates
                on the domain 'yoga-und-entspannung.ch'.
                """
                print("My Certificate Handler: ", err, url)
                return (url[:30]=="https://self-signed.badssl.com")
            CEFBrowser.certificate_error_handler = my_cert_handler
            return cb

    SimpleBrowserApp().run()

