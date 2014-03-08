'''
An example of embedding CEF browser in the Kivy framework.
The browser is embedded using off-screen rendering mode.

Tested using Kivy 1.7.2 stable on Ubuntu 12.04 64-bit.

In this example kivy-lang is used to declare the layout which
contains two buttons (back, forward) and the browser view.
'''

from kivy.app import App
from kivy.clock import Clock
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from lib.cefpython import *
from cefbrowser import CefBrowser


if __name__ == '__main__':
    class CefApp(App):
        def build(self):
            self.gl = GridLayout(cols=2)
            self.b1 = Button(text="Gaggi1", height=32, size_hint=(1, None))
            self.b2 = Button(text="Gaggi2", height=32, size_hint=(1, None))
            self.cb1 = CefBrowser(url=test_url)
            self.cb2 = CefBrowser(url="http://www.kivy.org")
            def set1(*largs):
                print "#########################################"
                print self.cb1, self.cb2
                self.cb1.url = "http://www.google.com"
            self.b1.bind(on_press=set1)
            def set2(*largs):
                print "#########################################"
                print self.cb2, self.cb1
                self.cb2.url = "http://www.google.com"
            self.b2.bind(on_press=set2)
            def didset1(*largs):
                print "#########################################"
                print largs
            self.cb1.bind(on_address_change=didset1)
            def didset2(*largs):
                print "#########################################"
                print largs
            self.cb2.bind(on_address_change=didset2)
            self.gl.add_widget(self.b1)
            self.gl.add_widget(self.b2)
            self.gl.add_widget(self.cb1)
            self.gl.add_widget(self.cb2)
            return self.gl
    CefApp().run()

    cefpython.Shutdown()
