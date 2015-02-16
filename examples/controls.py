#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Demo of a browser with control elements and a url-input.
Mixed with kv-language. => CEFBrowser gets added in controls.kv file.
"""

from kivy.app import App


if __name__ == '__main__':
    class ControlsApp(App):
        pass

    ControlsApp().run()

    cefpython.Shutdown()

