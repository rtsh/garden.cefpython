#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Example of the CEFBrowser widget embedded in a UI with tabs and controls, as
known from Chrome on Windows, Mac OS X or Linux.
"""


import functools
import os

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.factory import Factory
from kivy.garden.cefpython import CEFBrowser
from kivy.lang import Builder
from kivy.properties import *
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.stencilview import StencilView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget


controls_size = 36

class TabbedCEFBrowserTab(GridLayout):
    text = StringProperty()
    url = StringProperty()
    last_tab = None
    __tabbed_cef_browser = None
    __cef_browser = None
    def __init__(self, tabbed_cef_browser, url="", text="", cef_browser=None):
        super(TabbedCEFBrowserTab, self).__init__(rows=1, size_hint=(None, 1), width=controls_size*10)
        self.__tabbed_cef_browser = tabbed_cef_browser
        self.url = url
        self.text = text
        self.__toggle_button = ToggleButton(text=text, group="tabs", font_size=controls_size/2, size_hint=(1, 1), text_size=(controls_size*10, controls_size), shorten=True, shorten_from="right", valign="middle", padding_x=5)
        self.__toggle_button.bind(size=self.__toggle_button.setter("text_size"))
        self.add_widget(self.__toggle_button)
        self.__close_button = Button(text="X", background_color=(1,0,0,1), font_size=controls_size/2, size_hint=(None, 1), width=controls_size)
        self.__close_button.bind(on_press=self.close)
        def on_toggle_state(toggle_button, new_state):
            if new_state=="down":
                toggle_button.bold = True
                self.add_widget(self.__close_button)
                self.__tabbed_cef_browser._set_tab(self)
            else:
                toggle_button.bold = False
                self.remove_widget(self.__close_button)
        self.__toggle_button.bind(state=on_toggle_state)
        def on_text(self, new_text):
            self.__toggle_button.text = new_text
        self.bind(text=on_text)
        if cef_browser:
            self.__cef_browser = cef_browser
            self.__configure_cef_browser()
    
    def select(self):
        self.__toggle_button.trigger_action()
    
    def close(self, *largs):
        self.cef_browser._browser.CloseBrowser()
    
    @property
    def cef_browser(self):
        if not self.__cef_browser:
            self.__cef_browser = CEFBrowser(self.url)
            self.__configure_cef_browser()
        return self.__cef_browser
    
    def __configure_cef_browser(self):
        self.__cef_browser.popup_policy = CEFBrowser.always_allow_popups
        def popup_new_tab_handler(browser, popup_browser):
            self.__tabbed_cef_browser.add_tab(TabbedCEFBrowserTab(self.__tabbed_cef_browser, cef_browser=popup_browser))
        self.__cef_browser.popup_handler = popup_new_tab_handler
        def close_tab_handler(browser, *largs):
            self.__tabbed_cef_browser.remove_tab(self)
        self.__cef_browser.close_handler = close_tab_handler
        self.__cef_browser.bind(url=self.setter("url"))
        self.__cef_browser.bind(title=self.setter("text"))
        def on_load_start(browser, *largs):
            self.__tabbed_cef_browser._load_button.text = "Go" if self.__tabbed_cef_browser._url_input.focus else "x"
        def on_load_end(browser, *largs):
            self.__tabbed_cef_browser._load_button.text = "Go" if self.__tabbed_cef_browser._url_input.focus else "r"
            self.__tabbed_cef_browser._back_button.disabled = not self.__tabbed_cef_browser._current_browser.can_go_back
            self.__tabbed_cef_browser._forward_button.disabled = not self.__tabbed_cef_browser._current_browser.can_go_forward
        self.__cef_browser.bind(on_load_start=on_load_start)
        self.__cef_browser.bind(on_load_end=on_load_end)
        self.__cef_browser.bind(on_load_error=on_load_end)

class TabbedCEFBrowser(GridLayout):
    def __init__(self, urls=["http://www.rentouch.ch"], *largs, **dargs):
        super(TabbedCEFBrowser, self).__init__(cols=1, *largs, **dargs)
        gl = GridLayout(rows=1, size_hint=(1, None), height=controls_size)
        self.current_tab = None
        self.__tab_bar_scroll = ScrollView(size_hint=(1, 1))
        self.__tab_bar_grid = GridLayout(rows=1, size_hint=(None, 1))
        self.__tab_bar_grid.bind(minimum_width=self.__tab_bar_grid.setter("width"))
        last_tab = None
        for url in urls:
            this_tab = TabbedCEFBrowserTab(self, url, url)
            this_tab.last_tab = last_tab
            self.__tab_bar_grid.add_widget(this_tab)
            last_tab = this_tab
        self.current_tab = last_tab
        self.__tab_bar_scroll.add_widget(self.__tab_bar_grid)
        self.__tab_bar_scroll.bind(height=self.__tab_bar_grid.setter("height"))
        gl.add_widget(self.__tab_bar_scroll)
        self.__tab_bar_new = Button(text="+", font_size=controls_size/2, size_hint=(None, 1), width=controls_size)
        def on_new_tab(but):
            self.add_tab(TabbedCEFBrowserTab(self, "http://google.com", "Google"))
            def focus_url_input(*largs):
                self._url_input.focus = True
            Clock.schedule_once(focus_url_input, 0)
        self.__tab_bar_new.bind(on_press=on_new_tab)
        gl.add_widget(self.__tab_bar_new)
        self.__control_bar_grid = GridLayout(rows=1, size_hint=(1, None), height=controls_size)
        self._back_button = Button(text="<", font_size=controls_size/2, size_hint=(None, 1), width=controls_size)
        def on_back_press(back_button):
            self._current_browser.go_back()
        self._back_button.bind(on_press=on_back_press)
        self._forward_button = Button(text=">", font_size=controls_size/2, size_hint=(None, 1), width=controls_size)
        def on_forward_press(forward_button):
            self._current_browser.go_forward()
        self._forward_button.bind(on_press=on_forward_press)
        self._url_input = TextInput(text="http://", font_size=controls_size/2, size_hint=(1, 1), multiline=False)
        def on_url_focus(url_input, new_focus):
            if new_focus:
                def fn(*largs):
                    url_input.select_all()
                Clock.schedule_once(fn, 0)
                self._load_button.text = "Go"
            else:
                url_input.text = self._current_browser.url
                self._load_button.text = "x" if self._current_browser.is_loading else "r"
        self._url_input.bind(focus=on_url_focus)
        def on_url_validate(url_input):
            self._current_browser.url = self._url_input.text
        self._url_input.bind(on_text_validate=on_url_validate)
        self._load_button = Button(text="Go", font_size=controls_size/2, size_hint=(None, 1), width=controls_size)
        def on_load_button(load_button):
            if self._url_input.focus:
                self._current_browser.url = self._url_input.text
            elif self._current_browser.is_loading:
                self._current_browser.stop_loading()
            else:
                self._current_browser.reload()
        self._load_button.bind(on_press=on_load_button)
        self.__control_bar_grid.add_widget(self._back_button)
        self.__control_bar_grid.add_widget(self._forward_button)
        self.__control_bar_grid.add_widget(self._url_input)
        self.__control_bar_grid.add_widget(self._load_button)
        self._current_browser = CEFBrowser()
        self.add_widget(gl)
        self.add_widget(self.__control_bar_grid)
        self.add_widget(self._current_browser)
        self.select_first_tab()
    
    def select_first_tab(self):
        for tab in self.__tab_bar_grid.children:
            tab.select()
            break
    
    @property
    def tabs(self):
        return self.__tab_bar_grid.children
    
    def add_tab(self, new_tab):
        self.__tab_bar_grid.add_widget(new_tab)
        new_tab.select()
    
    def remove_tab(self, remove_tab):
        self.__tab_bar_grid.remove_widget(remove_tab)
        self.current_tab = remove_tab.last_tab
        remove_tab.last_tab.select()
    
    def _set_tab(self, new_tab):
        if self.current_tab!=new_tab:
            ct = self.current_tab
            tmp = ct
            while tmp:
                if tmp.last_tab==new_tab:
                    tmp.last_tab = new_tab.last_tab
                tmp = tmp.last_tab
            new_tab.last_tab = ct
            self.current_tab = new_tab
        def url_input_set_text(browser, url):
            self._url_input.text = url
            if self._url_input.focus:
                self._url_input.select_all()
        try:
            self._current_browser.unbind(url=url_input_set_text)
        except:
            pass
        def old_tab_remove_keyboard(browser, *largs):
            print "old_tab_remove_keyboard", browser
            browser.focus = False
        Clock.schedule_once(functools.partial(old_tab_remove_keyboard, self._current_browser))
        self.remove_widget(self._current_browser)
        self._url_input.text = new_tab.url
        self._current_browser = new_tab.cef_browser
        self.add_widget(self._current_browser)
        self._current_browser.bind(url=url_input_set_text)

if __name__ == '__main__':
    class CEFApp(App):
        def timeout(self, *largs):
            print "TABBED: Timeout over"
            tb = self.tb
            tb.height -= 100
            
        def build(self):
            Clock.schedule_once(self.timeout, 15)
            self.tb = TabbedCEFBrowser(urls=["http://jegger.ch/datapool/app/test_popup.html", "http://kivy.org",
                "https://github.com/kivy-garden/garden.cefpython", 
                "http://code.google.com/p/cefpython/",
                "http://code.google.com/p/chromiumembedded/", "about:blank"], pos=(20,10), size_hint=(None, None), size=(Window.width-40, Window.height-20))
            return self.tb

    CEFApp().run()

