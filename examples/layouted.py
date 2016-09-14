#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Displays the Browser inside a layout (for testing relative positions)
"""


from kivy.app import App
from kivy.uix.anchorlayout import AnchorLayout
from kivy.garden.cefpython import CEFBrowser


if __name__ == '__main__':
    class SimpleBrowserApp(App):
        def build(self):
            layout = AnchorLayout(padding=(50, 50))
            browser = CEFBrowser(url="http://html5demos.com/drag")
            layout.add_widget(browser)
            return layout

    SimpleBrowserApp().run()

