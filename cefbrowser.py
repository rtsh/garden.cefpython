'''
The CefBrowser Widget actually displays the browser. It displays ONLY the
browser:
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
from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import *
from kivy.uix.widget import Widget
from lib.cefpython import *
from cefkeyboard import CefKeyboardManager

class CefBrowser(Widget):
    # Keyboard mode: "global" or "local".
    # 1. Global mode forwards keys to CEF all the time.
    # 2. Local mode forwards keys to CEF only when an editable
    #    control is focused (input type=text|password or textarea).
    keyboard_mode = OptionProperty("local", options=("global", "local"))
    url = StringProperty("http://www.google.com")
    browser = None
    popup = None

    def __init__ (self, *largs, **dargs):
        super(CefBrowser, self).__init__()
        self.url = dargs.get("url", "http://www.google.com")
        self.keyboard_mode = dargs.get("keyboard_mode", "local")
        self.__rect = None
        self.browser = None
        self.popup = CefBrowserPopup(self)
        self.register_event_type("on_loading_state_change")
        self.register_event_type("on_address_change")
        self.register_event_type("on_title_change")
        self.register_event_type("on_before_popup")
        self.register_event_type("on_load_start")
        self.register_event_type("on_load_end")
        self.register_event_type("on_load_error")
        self.texture = Texture.create(size=self.size, colorfmt='rgba', bufferfmt='ubyte')
        self.texture.flip_vertical()
        with self.canvas:
            Color(1, 1, 1)
            self.__rect = Rectangle(pos=self.pos, size=self.size, texture=self.texture)
        windowInfo = cefpython.WindowInfo()
        windowInfo.SetAsOffscreen(0)
        self.browser = cefpython.CreateBrowserSync(windowInfo, {}, self.url)
        self.browser.SendFocusEvent(True)
        ch = ClientHandler(self)
        self.browser.SetClientHandler(ch)
        self.browser.WasResized()
        self.bind(size=self.realign)
        self.bind(pos=self.realign)
        self.bind(url=self.set_url)
        self.bind(keyboard_mode=self.set_keyboard_mode)
        if self.keyboard_mode == "global":
            self.request_keyboard()

    def realign(self, *largs):
        ts = self.texture.size
        ss = self.size
        schg = (ts[0]!=ss[0] or ts[1]!=ss[1])
        if schg:
            self.texture = Texture.create(size=self.size, colorfmt='rgba', bufferfmt='ubyte')
            self.texture.flip_vertical()
        if self.__rect:
            with self.canvas:
                Color(1, 1, 1)
                self.__rect.pos = self.pos
                if schg:
                    self.__rect.size = self.size
            if schg:
                self.update_rect()
        if self.browser:
            self.browser.WasResized()
            self.browser.NotifyScreenInfoChanged()
        # Bring keyboard to front
        try:
            k = self.__keyboard.widget
            p = k.parent
            p.remove_widget(k)
            p.add_widget(k)
        except:
            pass

    def update_rect(self):
        if self.__rect:
            self.__rect.texture = self.texture
    
    def set_url(self, *largs):
        self.browser.StopLoad()
        self.browser.Navigate(self.url)
    
    def set_keyboard_mode(self, *largs):
        if self.keyboard_mode == "global":
            self.request_keyboard()
        else:
            self.release_keyboard()
            self.browser.GetFocusedFrame().ExecuteJavascript("__kivy__keyboard_requested = false;")
    
    def on_loading_state_change(self, isLoading, canGoBack, canGoForward):
        pass
    
    def on_address_change(self, frame, url):
        pass
    
    def on_title_change(self, newTitle):
        pass
    
    def on_before_popup(self, frame, url):
        pass
    
    def on_load_start(self, frame):
        pass
    
    def on_load_end(self, frame, httpStatusCode):
        pass
    
    def on_load_error(self, frame, errorCode, errorText, failedUrl):
        pass

    __keyboard = None

    def request_keyboard(self):
        if not self.__keyboard:
            self.__keyboard = EventLoop.window.request_keyboard(
                    self.release_keyboard, self)
            self.__keyboard.bind(on_key_down=self.on_key_down)
            self.__keyboard.bind(on_key_up=self.on_key_up)
        CefKeyboardManager.reset_all_modifiers()
        # Not sure if it is still required to send the focus
        # (some earlier bug), but it shouldn't hurt to call it.
        self.browser.SendFocusEvent(True)

    def release_keyboard(self):
        # When using local keyboard mode, do all the request
        # and releases of the keyboard through js bindings,
        # otherwise some focus problems arise.
        CefKeyboardManager.reset_all_modifiers()
        if not self.__keyboard:
            return
        print("release_keyboard()")
        self.__keyboard.unbind(on_key_down=self.on_key_down)
        self.__keyboard.unbind(on_key_up=self.on_key_up)
        self.__keyboard.release()
        self.__keyboard = None

    def on_key_down(self, *largs):
        CefKeyboardManager.kivy_on_key_down(self.browser, *largs)

    def on_key_up(self, *largs):
        CefKeyboardManager.kivy_on_key_up(self.browser, *largs)

    def go_back(self):
        self.browser.GoBack()

    def go_forward(self):
        self.browser.GoForward()

    def on_touch_down(self, touch, *kwargs):
        if not self.collide_point(*touch.pos):
            return
        if self.keyboard_mode == "global":
            self.request_keyboard()
        else:
            Window.release_all_keyboards()
            self.browser.GetFocusedFrame().ExecuteJavascript("__kivy__keyboard_requested = false;")

        touch.grab(self)
        y = self.height-touch.pos[1] + self.pos[1]
        x = touch.x - self.pos[0]
        self.browser.SendMouseClickEvent(
            x,
            y,
            cefpython.MOUSEBUTTON_LEFT,
            mouseUp=False,
            clickCount=1
        )
        return True

    def on_touch_move(self, touch, *kwargs):
        if touch.grab_current is not self:
            return
        y = self.height-touch.pos[1] + self.pos[1]
        x = touch.x - self.pos[0]
        self.browser.SendMouseMoveEvent(x, y, mouseLeave=False)
        return True

    def on_touch_up(self, touch, *kwargs):
        if touch.grab_current is not self:
            return
        y = self.height-touch.pos[1] + self.pos[1]
        x = touch.x - self.pos[0]
        self.browser.SendMouseClickEvent(
            x,
            y,
            cefpython.MOUSEBUTTON_LEFT,
            mouseUp=True, clickCount=1
        )
        touch.ungrab(self)
        return True


class CefBrowserPopup(Widget):
    rx = NumericProperty(0)
    ry = NumericProperty(0)
    rpos = ReferenceListProperty(rx, ry)
    
    def __init__ (self, parent, *largs, **dargs):
        super(CefBrowserPopup, self).__init__()
        self.browser_widget = parent
        self.__rect = None
        self.texture = Texture.create(size=self.size, colorfmt='rgba', bufferfmt='ubyte')
        self.texture.flip_vertical()
        with self.canvas:
            Color(1, 1, 1)
            self.__rect = Rectangle(pos=self.pos, size=self.size, texture=self.texture)
        self.bind(rpos=self.realign)
        self.bind(size=self.realign)
        parent.bind(pos=self.realign)
        parent.bind(size=self.realign)
    
    def realign(self, *largs):
        self.x = self.rx+self.browser_widget.x
        self.y = self.browser_widget.height-self.ry-self.height+self.browser_widget.y
        ts = self.texture.size
        ss = self.size
        schg = (ts[0]!=ss[0] or ts[1]!=ss[1])
        if schg:
            self.texture = Texture.create(size=self.size, colorfmt='rgba', bufferfmt='ubyte')
            self.texture.flip_vertical()
        if self.__rect:
            with self.canvas:
                Color(1, 1, 1)
                self.__rect.pos = self.pos
                if schg:
                    self.__rect.size = self.size
            if schg:
                self.update_rect()

    def update_rect(self):
        if self.__rect:
            self.__rect.texture = self.texture

class ClientHandler():
    def __init__(self, browserWidget):
        self.browser_widget = browserWidget
    
    # DisplayHandler
    
    def OnLoadingStateChange(self, browser, isLoading, canGoBack, canGoForward):
        self.browser_widget.dispatch("on_loading_state_change", isLoading, canGoBack, canGoForward)
    
    def OnAddressChange(self, browser, frame, url):
        self.browser_widget.dispatch("on_address_change", frame, url)
    
    def OnTitleChange(self, browser, newTitle):
        self.browser_widget.dispatch("on_title_change", newTitle)
     
    def OnTooltip(self, *largs):
        return True
    
    def OnStatusMessage(self, *largs):
        pass
    
    def OnConsoleMessage(self, *largs):
        pass
    
    # DownloadHandler
    
    # DragHandler
    
    # JavascriptContextHandler
    
    # KeyboardHandler
    
    def OnPreKeyEvent(self, *largs):
        pass
    
    def OnKeyEvent(self, *largs):
        pass
        
    # LifeSpanHandler

    def OnBeforePopup(self, browser, frame, url, *largs):
        self.browser_widget.dispatch("on_before_popup", frame, url)
        return True
    
    # LoadHandler
    
    def OnLoadStart(self, browser, frame):
        self.browser_widget.dispatch("on_load_start", frame)
        bw = self.browser_widget
        if bw and bw.keyboard_mode == "local":
            print("OnLoadStart(): injecting focus listeners for text controls")
            # The logic is similar to the one found in kivy-berkelium:
            # https://github.com/kivy/kivy-berkelium/blob/master/berkelium/__init__.py
            jb = cefpython.JavascriptBindings(bindToFrames=True, bindToPopups=True)
            jb.SetFunction("__kivy__request_keyboard", self.browser_widget.request_keyboard)
            jb.SetFunction("__kivy__release_keyboard", self.browser_widget.release_keyboard)
            self.browser_widget.browser.SetJavascriptBindings(jb)
            jsCode = """
                var __kivy__keyboard_requested = false;
                function __kivy__keyboard_interval() {
                    var element = document.activeElement;
                    if (!element) {
                        return;
                    }
                    var tag = element.tagName.toUpperCase();
                    var type = element.type;
                    if (tag == "INPUT" && (type == "" || type == "text"
                            || type == "password") || tag == "TEXTAREA") {
                        if (!__kivy__keyboard_requested) {
                            __kivy__request_keyboard();
                            __kivy__keyboard_requested = true;
                        }
                        return;
                    }
                    if (__kivy__keyboard_requested) {
                        __kivy__release_keyboard();
                        __kivy__keyboard_requested = false;
                    }
                }
                function __kivy__on_escape() {
                    if (document.activeElement) {
                        document.activeElement.blur();
                    }
                    if (__kivy__keyboard_requested) {
                        __kivy__release_keyboard();
                        __kivy__keyboard_requested = false;
                    }
                }
                setInterval(__kivy__keyboard_interval, 100);
            """
            frame.ExecuteJavascript(jsCode)
    
    def OnLoadEnd(self, browser, frame, httpStatusCode):
        self.browser_widget.dispatch("on_load_end", frame, httpStatusCode)
        #browser.SetZoomLevel(2.0) # this works at this point
    
    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        self.browser_widget.dispatch("on_load_error", frame, errorCode, errorText, failedUrl)
    
    def OnRendererProcessTerminated(self, *largs):
        pass
    
    # RenderHandler
    
    def GetRootScreenRect(self, *largs):
        return False
    
    def GetViewRect(self, browser, rect):
        width, height = self.browser_widget.texture.size
        rect.append(0)
        rect.append(0)
        rect.append(width)
        rect.append(height)
        return True
    
    def GetScreenPoint(self, *largs):
        pass
    
    def GetScreenInfo(self, *largs):
        pass

    def OnPopupShow(self, browser, shown):
        self.browser_widget.remove_widget(self.browser_widget.popup)
        if shown:
            self.browser_widget.add_widget(self.browser_widget.popup)
    
    def OnPopupSize(self, browser, rect):
        print "NEW RECT", rect
        self.browser_widget.popup.rpos = (rect[0], rect[1])
        self.browser_widget.popup.size = (rect[2], rect[3])
         
    def OnPaint(self, browser, paintElementType, dirtyRects, buf, width, height):
        b = buf.GetString(mode="bgra", origin="top-left")
        bw = self.browser_widget
        if paintElementType != cefpython.PET_VIEW:
            if bw.popup.texture.width*bw.popup.texture.height*4!=len(b):
                return True # prevent segfault
            bw.popup.texture.blit_buffer(b, colorfmt='bgra', bufferfmt='ubyte')
            bw.popup.update_rect()
            return True
        if bw.texture.width*bw.texture.height*4!=len(b):
            return True # prevent segfault
        bw.texture.blit_buffer(b, colorfmt='bgra', bufferfmt='ubyte')
        bw.update_rect()
        return True
     
    def OnCursorChange(self, *largs):
        pass
    
    def OnScrollOffsetChanged(self, *largs):
        pass
    
    # RequestHandler
    
    def OnBeforeBrowse(self, *largs):
        pass
    
    def OnBeforeResourceLoad(self, *largs):
        pass
    
    def GetResourceHandler(self, *largs):
        pass
    
    def OnResourceRedirect(self, *largs):
        pass
    
    def GetAuthCredentials(self, *largs):
        pass
    
    def OnQuotaRequest(self, *largs):
        pass
    
    def GetCookieManager(self, *largs):
        pass
    
    def OnProtocolExecution(self, *largs):
        pass
    
    # RessourceHandler


if __name__ == '__main__':
    class CefApp(App):
        def timeout(self, cb, *largs):
            self.cb.url = test_url
            #self.cb.keyboard_mode = "global"
        def build(self):
            self.cb = CefBrowser(url="http://kivy.org")
            Clock.schedule_once(self.timeout, 5)
            return self.cb

    CefApp().run()

    cefpython.Shutdown()

