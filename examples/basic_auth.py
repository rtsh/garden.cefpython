#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
This is here to test basic-auth.
"""


from kivy.app import App
from kivy.garden.cefpython import CEFBrowser


if __name__ == '__main__':
    class SimpleBrowserApp(App):
        def build(self):
            return CEFBrowser(url="https://httpbin.org/basic-auth/user/passwd")

    SimpleBrowserApp().run()
