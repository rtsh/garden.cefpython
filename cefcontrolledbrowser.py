'''
The CefControlledBrowser Widget displays a browser with user controls:
- If you want only the browser window, use cefbrowser.CefBrowser
- If you want a single browser with controls (like "back", "forward", url
    input, etc.), use cefcontrolledbrowser.CefControlledBrowser
- If you want a browser with tabs, user ceftabbedbrowser.CefTabbedBrowser

You can subclass all those Widgets and modify some of their methods to make
them look differently. e.g. you can make a tabbed browser which yet has no 
controls on each tab (by overriding CefTabbedBrowser.get_browser and replacing
CefControlledBrowser with CefBrowser)
'''

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import *
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from cefbrowser import CefBrowser
from lib.cefpython import *
import re

class CefControlledBrowser(Widget):
    navigation_bar_hei = NumericProperty(32)
    
    def __init__ (self, *largs, **dargs):
        super(CefControlledBrowser, self).__init__()
        initBrowser = dargs.get("browser", False)
        initUrl = dargs.get("url", "http://www.google.com")
        if initBrowser:
            initUrl = initBrowser.url
        else:
            initBrowser = CefBrowser(url=initUrl)
        self.back_button = self.get_back_button()
        self.add_widget(self.back_button)
        self.forward_button = self.get_forward_button()
        self.add_widget(self.forward_button)
        self.stop_reload_button = self.get_stop_reload_button()
        self.add_widget(self.stop_reload_button)
        self.url_input = self.get_url_input(initUrl)
        self.add_widget(self.url_input)
        self.cef_browser = initBrowser
        self.add_widget(self.cef_browser)
        self.configure_cef_browser(initBrowser)
        self.bind(pos=self.realign)
        self.bind(size=self.realign)
        self.bind(navigation_bar_hei=self.set_navigation_bar_hei)

    def get_back_button(self):
        bb = Button(text="<")
        def go_back(*largs):
            self.cef_browser._browser.GoBack()
        bb.bind(on_press=go_back)
        return bb
    def get_forward_button(self):
        fb = Button(text=">")
        def go_forward(*largs):
            self.cef_browser._browser.GoForward()
        fb.bind(on_press=go_forward)
        return fb
    def get_stop_reload_button(self):
        srb = Button(text="x")
        def stop_reload(*largs):
            if self.stop_reload_button.text=="r":
                self.cef_browser._browser.Reload()
            else:
                self.cef_browser._browser.StopLoad()
        srb.bind(on_press=stop_reload)
        return srb
    def get_url_input(self, initUrl):
        ui = TextInput(input_type="url", multiline=False)
        ui.bind(on_text_validate=self.change_url)
        def select_all(*largs):
            if self.url_input.focus:
                def do_select_all(*largs):
                    self.url_input.select_all()
                Clock.schedule_once(do_select_all, 0)
        ui.bind(focus=select_all)
        ui.go = Button(text="Go")
        ui.go.bind(on_press=self.change_url)
        self.add_widget(ui.go)
        return ui
    def configure_cef_browser(self, cb):
        def on_url(cb, url):
            self.url_input.text = url
        cb.bind(url=on_url)
        self.url_input.text = cb.url
        def on_load_start(cb, frame):
            self.stop_reload_button.text = "x"
        cb.bind(on_load_start=on_load_start)
        def on_load_end(cb, frame, *largs):
            self.stop_reload_button.text = "r"
            self.back_button.disabled = (not self.cef_browser._browser.CanGoBack())
            self.forward_button.disabled = (not self.cef_browser._browser.CanGoForward())
        cb.bind(on_load_end=on_load_end)
        cb.bind(on_load_error=on_load_end)
        return cb

    def set_navigation_bar_hei(self, *largs):
        self.realign()
    
    def realign(self, *largs):
        self.realign_back_button(self.back_button)
        self.realign_forward_button(self.forward_button)
        self.realign_stop_reload_button(self.stop_reload_button)
        self.realign_url_input(self.url_input)
        self.realign_cef_browser(self.cef_browser)

    def realign_back_button(self, bb):
        nbh = self.navigation_bar_hei
        bb.pos = (self.x+0*nbh, self.y+self.height-nbh)
        bb.size = (nbh, nbh)
    def realign_forward_button(self, fb):
        nbh = self.navigation_bar_hei
        fb.pos = (self.x+1*nbh, self.y+self.height-nbh)
        fb.size = (nbh, nbh)
    def realign_stop_reload_button(self, srb):
        nbh = self.navigation_bar_hei
        srb.pos = (self.x+2*nbh, self.y+self.height-nbh)
        srb.size = (nbh, nbh)
    def realign_url_input(self, ui):
        nbh = self.navigation_bar_hei
        ui.pos = (self.x+3*nbh, self.y+self.height-nbh)
        ui.size = (self.width-4*nbh, nbh)
        ui.go.pos = (self.x+self.width-nbh, self.y+self.height-nbh)
        ui.go.size = (nbh, nbh)
    def realign_cef_browser(self, cb):
        nbh = self.navigation_bar_hei
        cb.pos = (self.x, self.y)
        cb.size = (self.width, self.height-nbh)
    
    def change_url(self, *largs):
        url = self.url_input.text
        if not re.match("^[a-zA-Z][a-zA-Z0-9\+\.\-]*\:\/\/", url):
            url = "http://"+url
        self.cef_browser.url = url
        self.url_input.select_text(len(url), len(url))
        self.url_input.focus = False


if __name__ == '__main__':
    class CefApp(App):
        def timeout(self, *largs):
            self.cb.navigation_bar_hei = 26
            self.cb.cef_browser.url = "http://jegger.ch/datapool/app/test_popup.html"
        def build(self):
            self.cb = CefControlledBrowser(url="http://kivy.org")
            Clock.schedule_once(self.timeout, 3)
            return self.cb

    CefApp().run()

    cefpython.Shutdown()

