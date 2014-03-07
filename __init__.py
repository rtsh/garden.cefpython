'''
An example of embedding CEF browser in the Kivy framework.
The browser is embedded using off-screen rendering mode.

Tested using Kivy 1.7.2 stable on Ubuntu 12.04 64-bit.

In this example kivy-lang is used to declare the layout which
contains two buttons (back, forward) and the browser view.
'''

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from lib.cefpython import *
from cefbrowser import CefBrowser


if __name__ == '__main__':

    Builder.load_string("""
<BrowserLayout>:
    orientation: 'vertical'
    BoxLayout:
        size_hint_y: None
        height: '48dp'
        Button:
            text: "Back"
            on_press: browser.go_back()
        Button:
            text: "Forward"
            on_press: browser.go_forward()
    CefBrowser:
        id: browser

""")

    class BrowserLayout(BoxLayout):
        pass

    class CefBrowserApp(App):
        def build(self):
            return CefBrowser(url="file:///home/rentouch/cef/cefpython/cefpython/cef3/linux/binaries_64bit/wxpython.html")
            #return BrowserLayout()
    CefBrowserApp().run()

    cefpython.Shutdown()
