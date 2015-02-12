'''
The CefTabbedBrowser Widget displays a browser with tabs:
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
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.stencilview import StencilView
from kivy.uix.widget import Widget
from cefbrowser import CefBrowser
from cefcontrolledbrowser import CefControlledBrowser
from lib.cefpython import *
import functools

class CefTabbedBrowser(Widget):
    tabs = ListProperty([])
    selected_tab = NumericProperty(0)
    tab_bar_height = NumericProperty(32)
    min_tab_wid = 200
    __displayed_tab = 0
    __displayed_browser = None
    
    def __init__ (self, *largs, **dargs):
        super(CefTabbedBrowser, self).__init__()
        initUrls = dargs.get("urls", ["http://www.google.com"])
        self.selected_tab = dargs.get("selected_tab", 0)
        self.tab_bar = self.get_tab_bar()
        self.add_widget(self.tab_bar)
        for i in range(len(initUrls)):
            self.new_tab(url=initUrls[i])
        self.realign()
        self.bind(pos=self.realign)
        self.bind(size=self.realign)
        self.bind(selected_tab=self.set_selected_tab)
        self.bind(tab_bar_height=self.realign)

    def get_browser(self, **dargs):
        cb = CefControlledBrowser(**dargs)
        def titlechangetab(index, obj, newTitle):
            self.tabs[index]["button"].label.text = newTitle
            return True
        fn = functools.partial(titlechangetab, self.selected_tab)
        cb.cef_browser.bind(on_title_change=fn)
        def popup_always(obj, url):
            return True
        def popup_new_tab(obj, browser):
            self.new_tab(browser=browser)
            self.selected_tab = len(self.tabs)-1
        def close_tab(cb, obj):
            for t in self.tabs:
                if t["browser"]==cb:
                    self.close_tab(t["button"])
        fn = functools.partial(close_tab, cb)
        cb.cef_browser.popup_policy = popup_always
        cb.cef_browser.popup_handler = popup_new_tab
        cb.cef_browser.close_handler = fn
        return cb

    def get_tab_bar(self):
        w = Widget()
        gl = GridLayout(rows=1, spacing=0, size_hint_x=None)
        gl.bind(minimum_width=gl.setter("width"))
        sv = ScrollView(size_hint=(None, None), size=(400, 400))
        sv.add_widget(gl)
        sv.bind(height=gl.setter("height"))
        w.add_widget(sv)
        b = Button(text="+")
        b.bind(on_press=functools.partial(self.new_tab, "http://olzimmerberg.ch"))
        w.add_widget(b)
        w.scroll_view = sv
        w.grid_layout = gl
        w.new_tab = b
        return w
    def get_tab(self, url):
        def on_tab_press(b):
            self.selected_tab = b.index
        b = Button(text="")
        b.bind(on_press=on_tab_press)
        l = Label(text=url, size=(250, self.tab_bar_height))
        s = StencilView()
        s.add_widget(l)
        b.add_widget(s)
        def set_lab_wid(l, *largs):
            l.width = l.texture_size[0]
        l.bind(texture_size=functools.partial(set_lab_wid, l))
        c = Button(text="x", background_color=(1, 0, 0, 1))
        c.bind(on_press=functools.partial(self.close_tab, b))
        b.add_widget(c)
        b.stencil = s
        b.label = l
        b.close = c
        return b

    def realign(self, *largs):
        tb = self.tab_bar
        tb.pos = (self.x, self.y+self.height-self.tab_bar_height)
        tb.size = (self.width-self.tab_bar_height, self.tab_bar_height)
        tb.scroll_view.pos = (self.x, self.y+self.height-self.tab_bar_height)
        tb.scroll_view.size = (self.width-self.tab_bar_height, self.tab_bar_height)
        tb.new_tab.pos = (self.x+self.width-self.tab_bar_height, self.y+self.height-self.tab_bar_height)
        tb.new_tab.size = (self.tab_bar_height, self.tab_bar_height)
        cb = self.__displayed_browser
        if cb:
            cb.pos = self.pos
            cb.size = (self.size[0], self.size[1]-self.tab_bar_height)
        else:
            self.set_selected_tab()
    def realign_tab(self, button, *largs):
        button.close.size = (16, 16)        
        button.stencil.pos = (button.x+5, button.y)
        button.stencil.size = (button.width-15-button.close.width, button.height)
        button.label.pos = button.stencil.pos
        button.label.height = button.stencil.height
        button.close.pos = (button.x+button.width-5-button.close.width, button.y+(button.height-button.close.height)/2)
    def rebuild_tabs(self):
        for i in range(len(self.tabs)):
            b = self.tabs[i]["button"]
            b.index = i
     
    def set_selected_tab(self, *largs):
        self.tabs[self.__displayed_tab]["button"].background_color = (1, 1, 1, 1)
        if self.__displayed_browser:
            self.__displayed_browser.cef_browser.release_keyboard()
            self.remove_widget(self.__displayed_browser)
        self.tabs[self.selected_tab]["button"].background_color = (0.5, 0.5, 0.5, 1)
        if not self.tabs[self.selected_tab]["browser"]:
            self.tabs[self.selected_tab]["browser"] = self.get_browser(url=self.tabs[self.selected_tab]["url"])
        cb = self.tabs[self.selected_tab]["browser"]
        cb.pos = self.pos
        cb.size = (self.size[0], self.size[1]-self.tab_bar_height)
        self.add_widget(cb)
        self.__displayed_browser = cb
        self.__displayed_tab = self.selected_tab

    def new_tab(self, *largs, **dargs):
        i = dargs.get("index", len(self.tabs))
        browser = dargs.get("browser", False)
        url = "http://google.com"
        if browser:
            url = browser.url
            browser = self.get_browser(browser=browser)
        else:
            url = dargs.get("url", url)
        i = dargs.get("index", len(self.tabs))
        b = self.get_tab(url)
        b.bind(pos=self.realign_tab)
        b.bind(size=self.realign_tab)
        b.index = i
        self.tabs.append({"url":url, "browser":browser, "button":b})
        self.tab_bar.grid_layout.clear_widgets()
        for tab in self.tabs:
            b = tab["button"]
            b.size_hint_x = None
            b.width = self.min_tab_wid
            self.tab_bar.grid_layout.add_widget(b)
        self.rebuild_tabs()
        self.realign()

    def close_tab(self, button, *largs):
        if len(self.tabs)==1:
            return
        self.remove_widget(self.__displayed_browser)
        i = button.index
        newdt = self.__displayed_tab
        if self.__displayed_tab>i and self.__displayed_tab!=0:
            newdt = self.__displayed_tab-1
        if newdt==len(self.tabs)-1:
            newdt -= 1
        b = self.tabs[i]["button"]
        b.parent.remove_widget(b)
        self.tabs.pop(i)
        self.__displayed_tab = newdt
        self.selected_tab = newdt
        self.set_selected_tab()
        self.rebuild_tabs()


if __name__ == '__main__':
    class CefApp(App):
        def timeout(self, *largs):
            tb = self.tb
            tb.tab_bar_height = 26
            tb.tabs[tb.selected_tab]["browser"].navigation_bar_hei = 26
            
        def build(self):
            Clock.schedule_once(self.timeout, 5)
            self.tb = CefTabbedBrowser(urls=["http://jegger.ch/datapool/app/test_popup.html", "http://kivy.org",
                "https://github.com/kivy-garden/garden.cefpython", 
                "http://code.google.com/p/cefpython/",
                "http://code.google.com/p/chromiumembedded/"])
            return self.tb

    CefApp().run()

    cefpython.Shutdown()

