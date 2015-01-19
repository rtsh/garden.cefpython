'''
The CefBrowser Widget actually displays the browser. It displays ONLY the
browser:
- If you want only the browser window, use cefbrowser.CefBrowser
- If you want a single browser with controls (like "back", "forward", url
    input, etc.), use cefcontrolledbrowser.CefControlledBrowser
- If you want a browser with tabs, use ceftabbedbrowser.CefTabbedBrowser

You can subclass all those Widgets and modify some of their methods to make
them look differently. e.g. you can make a tabbed browser which yet has no 
controls on each tab (by overriding CefTabbedBrowser.get_browser and replacing
CefControlledBrowser with CefBrowser)
'''

from kivy.base import EventLoop
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import *
from kivy.uix.widget import Widget
from lib.cefpython import cefpython
from cefkeyboard import CefKeyboardManager

class CefBrowser(Widget):
    # Keyboard mode: "global" or "local".
    # 1. Global mode forwards keys to CEF all the time.
    # 2. Local mode forwards keys to CEF only when an editable
    #    control is focused (input type=text|password or textarea).
    keyboard_mode = OptionProperty("local", options=("global", "local"))
    url = StringProperty("about:blank")
    browser = None
    popup = None
    __rect = None
    __js_bindings = None  # See bind_js()
    __reset_js_bindings = False  # TODO: Is this right?!? See bind_js()

    def __init__ (self, *largs, **dargs):
        self.url = dargs.pop("url", "about:blank")
        self.keyboard_mode = dargs.pop("keyboard_mode", "local")
        self.browser = dargs.pop("browser", None)
        self.popup = CefBrowserPopup(self)
        self.__rect = None
        self.__js_bindings = None
        self.__reset_js_bindings = False
        super(CefBrowser, self).__init__(**dargs)

        self.register_event_type("on_loading_state_change")
        self.register_event_type("on_address_change")
        self.register_event_type("on_title_change")
        self.register_event_type("on_before_popup")
        self.register_event_type("on_load_start")
        self.register_event_type("on_load_end")
        self.register_event_type("on_load_error")
        self.register_event_type("on_certificate_error")
        self.register_event_type("on_js_dialog")
        self.register_event_type("on_before_unload_dialog")

        self.texture = Texture.create(size=self.size, colorfmt='rgba', bufferfmt='ubyte')
        self.texture.flip_vertical()
        with self.canvas:
            Color(1, 1, 1)
            self.__rect = Rectangle(pos=self.pos, size=self.size, texture=self.texture)

        if not self.browser:
            windowInfo = cefpython.WindowInfo()
            windowInfo.SetAsOffscreen(0)
            self.browser = cefpython.CreateBrowserSync(windowInfo, {}, navigateUrl=self.url)
            self.browser.SetClientHandler(client_handler)

        client_handler.browser_widgets[self.browser] = self
        self.browser.SendFocusEvent(True)
        #self.bind_js() # TODO: delete?
        self.browser.WasResized()
        self.bind(size=self.realign)
        self.bind(pos=self.realign)
        self.bind(keyboard_mode=self.set_keyboard_mode)
        if self.keyboard_mode == "global":
            self.request_keyboard()

    def bind_js(self):
        # Needed to introduce bind_js again because the freeze of sites at load took over.
        # As an example 'http://www.htmlbasix.com/popup.shtml' freezed every time. By setting the js
        # bindings again, the freeze rate is at about 35%. Check git to see how it was done, before using
        # this function ...
        # I (jegger) have to be honest, that I don't have a clue why this is acting like it does!
        # I hope simon (REN-840) can resolve this once in for all...
        #
        # ORIGINAL COMMENT:
        # When browser.Navigate() is called, some bug appears in CEF
        # that makes CefRenderProcessHandler::OnBrowserDestroyed()
        # is being called. This destroys the javascript bindings in
        # the Render process. We have to make the js bindings again,
        # after the call to Navigate() when OnLoadingStateChange()
        # is called with isLoading=False. Problem reported here:
        # http://www.magpcss.org/ceforum/viewtopic.php?f=6&t=11009
        if not self.__js_bindings:
            self.__js_bindings = cefpython.JavascriptBindings(bindToFrames=True, bindToPopups=True)
            self.__js_bindings.SetFunction("__kivy__keyboard_update", self.keyboard_update)
        self.browser.SetJavascriptBindings(self.__js_bindings)

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

    def on_url(self, instance, value):
        print "ON URL", instance, value, self.browser.GetUrl()
        if self.browser and value:
            self.browser.Navigate(self.url)
            self.__reset_js_bindings = True

    def set_keyboard_mode(self, *largs):
        if self.keyboard_mode == "global":
            self.request_keyboard()
        else:
            self.release_keyboard()

    def on_loading_state_change(self, isLoading, canGoBack, canGoForward):
        self.is_loading = isLoading

    def on_address_change(self, frame, url):
        self.url = url

    def on_title_change(self, newTitle):
        pass

    def on_before_popup(self, browser, frame, targetUrl, targetFrameName,
            popupFeatures, windowInfo, client, browserSettings, noJavascriptAccess):
        pass

    def on_js_dialog(self, browser, origin_url, accept_lang, dialog_type, message_text, default_prompt_text, callback,
                     suppress_message):
        pass

    def on_before_unload_dialog(self, browser, message_text, is_reload, callback):
        pass

    def on_certificate_error(self, err, url, cb):
        print "on_certificate_error", err, url
        cb.Continue(False)

    def on_load_start(self, frame):
        pass

    def on_load_end(self, frame, httpStatusCode):
        pass

    def on_load_error(self, frame, errorCode, errorText, failedUrl):
        print("on_load_error=> Code: %s, errorText: %s, failedURL: %s" % (errorCode, errorText, failedUrl))
        pass

    def OnCertificateError(self, err, url, cb):
        print "OnCertificateError", err, url, cb
        # Check if cert verification is disabled
        if os.path.isfile("/etc/rentouch/ssl-verification-disabled"):
            cb.Continue(True)
        else:
            self.dispatch("on_certificate_error", err, url, cb)

    __keyboard = None

    def keyboard_update(self, shown, rect, attributes):
        """
        :param shown: Show keyboard if true, hide if false (blur)
        :param rect: [x,y,width,height] of the input element
        :param attributes: Attributes of HTML element
        """
        if shown:
            # Check if keyboard should get displayed above
            above = False
            if 'class' in attributes:
                if attributes['class'] in self.keyboard_above_classes:
                    above = True

            self.request_keyboard()
            kb = self.__keyboard.widget
            if len(rect) < 4:
                kb.pos = ((Window.width-kb.width*kb.scale)/2, 10)
            else:
                x = self.x+rect[0]+(rect[2]-kb.width*kb.scale)/2
                y = self.height+self.y-rect[1]-rect[3]-kb.height*kb.scale
                if above:
                    # If keyboard should displayed above the input field
                    # Above is good on e.g. search boxes with results displayed
                    # bellow the input field
                    y = self.height+self.y-rect[1]
                if y < 0:
                    # If keyboard escapes viewport at bottom
                    rightx = self.x+rect[0]+rect[2]
                    spleft = self.x+rect[0]
                    spright = Window.width-rightx
                    y = 0
                    if spleft <= spright:
                        x = rightx
                    else:
                        x = spleft-kb.width*kb.scale
                elif y+kb.height*kb.scale > Window.height:
                    # If keyboard escapes viewport at top
                    rightx = self.x+rect[0]+rect[2]
                    spleft = self.x+rect[0]
                    spright = Window.width-rightx
                    y = Window.height-kb.height*kb.scale
                    if spleft <= spright:
                        x = rightx
                    else:
                        x = spleft-kb.width*kb.scale
                else:
                    if x < 0:
                        x = 0
                    elif Window.width < x+kb.width*kb.scale:
                        x = Window.width-kb.width*kb.scale
                kb.pos = (x, y)
        else:
            self.release_keyboard()

    def request_keyboard(self):
        print("REQUEST KB")
        if not self.__keyboard:
            self.__keyboard = EventLoop.window.request_keyboard(
                    self.release_keyboard, self)
            self.__keyboard.bind(on_key_down=self.on_key_down)
            self.__keyboard.bind(on_key_up=self.on_key_up)
        CefKeyboardManager.reset_all_modifiers()
        # Not sure if it is still required to send the focus
        # (some earlier bug), but it shouldn't hurt to call it.
        self.browser.SendFocusEvent(True)

    def release_keyboard(self, *kwargs):
        print("RELEASE KB")
        # When using local keyboard mode, do all the request
        # and releases of the keyboard through js bindings,
        # otherwise some focus problems arise.
        CefKeyboardManager.reset_all_modifiers()
        if not self.__keyboard:
            return
        self.__keyboard.unbind(on_key_down=self.on_key_down)
        self.__keyboard.unbind(on_key_up=self.on_key_up)
        self.__keyboard.release()
        self.__keyboard = None
        self.browser.SendFocusEvent(False)

    def on_key_down(self, *largs):
        print("KEY DOWN", largs)
        CefKeyboardManager.kivy_on_key_down(self.browser, *largs)

    def on_key_up(self, *largs):
        print("KEY UP", largs)
        CefKeyboardManager.kivy_on_key_up(self.browser, *largs)

    def go_back(self):
        self.browser.GoBack()

    def go_forward(self):
        self.browser.GoForward()

    def delete_cookie(self, url=""):
        """ Deletes the cookie with the given url. If url is empty all cookies get deleted.
        """
        cookie_manager = cefpython.CookieManager.GetGlobalManager()
        if cookie_manager:
            cookie_manager.DeleteCookies(url, "")
        else:
            print("No cookie manager found!, Can't delete cookie(s)")

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

    def __init__(self, parent, *largs, **dargs):
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
    browser_widgets = {}

    def __init__(self, *largs):
        self.browser_widgets = {}

    # DisplayHandler

    def OnLoadingStateChange(self, browser, isLoading, canGoBack, canGoForward):
        bw = self.browser_widgets[browser]
        bw.dispatch("on_loading_state_change", isLoading, canGoBack, canGoForward)
        """ TODO: Delete?
        if bw.__reset_js_bindings and not isLoading:
            if bw:
                bw.set_js_bindings()
        """
        if not isLoading and bw:
            bw.bind_js()
        if isLoading and bw and bw.keyboard_mode == "local":
            # Release keyboard when navigating to a new page.
            bw.release_keyboard()

    def OnAddressChange(self, browser, frame, url):
        self.browser_widgets[browser].dispatch("on_address_change", frame, url)

    def OnTitleChange(self, browser, newTitle):
        self.browser_widgets[browser].dispatch("on_title_change", newTitle)

    def OnTooltip(self, *largs):
        return True

    def OnStatusMessage(self, *largs):
        pass

    def OnConsoleMessage(self, *largs):
        pass

    # DownloadHandler

    # DragHandler

    # JavascriptContextHandler
    """
    def OnJSDialog(self, *kwargs):
        #self.browser_widgets["TODO"].dispatch("on_js_dialog", *kwargs)
        return True

    def OnBeforeUnloadDialog(self, *kwargs):
        #self.browser_widgets["TODO"].dispatch("on_before_unload_dialog", *kwargs)
        return True
    """

    # KeyboardHandler

    def OnPreKeyEvent(self, *largs):
        pass

    def OnKeyEvent(self, *largs):
        pass

    # LifeSpanHandler

    def OnBeforePopup(self, browser, frame, targetUrl, targetFrameName, popupFeatures, windowInfo, client, browserSettings, *largs):
        print "On Before Popup", targetUrl
        wi = cefpython.WindowInfo()
        wi.SetAsChild(0)
        wi.SetAsOffscreen(0)
        windowInfo.append(wi)
        browserSettings.append({})
        return False

    def RunModal(self, browser, *largs):
        print "Run Modal"
        return False

    def DoClose(self, browser, *largs):
        print "Do Close", browser
        bw = self.browser_widgets[browser]
        bw.parent.remove_widget(bw)
        del bw
        return False

    def OnBeforeClose(self, browser, *largs):
        print "On Before Close"

    # LoadHandler

    def OnLoadStart(self, browser, frame):
        bw = self.browser_widgets[browser]
        bw.dispatch("on_load_start", frame)
        if bw and bw.keyboard_mode == "local":
            lrectconstruct = "var rect = e.target.getBoundingClientRect();var lrect = [rect.left, rect.top, rect.width, rect.height];"
            if frame.GetParent():
                lrectconstruct = "var lrect = [];"
            jsCode = """
window.print = function () {
    console.log("Print dialog blocked");
};
function isKeyboardElement(elem) {
    var tag = elem.tagName.toUpperCase();
    if (tag=="INPUT") return (["TEXT", "PASSWORD", "DATE", "DATETIME", "DATETIME-LOCAL", "EMAIL", "MONTH", "NUMBER", "SEARCH", "TEL", "TIME", "URL", "WEEK"].indexOf(elem.type.toUpperCase())!=-1);
    else if (tag=="TEXTAREA") return true;
    else {
        var tmp = elem;
        while (tmp && tmp.contentEditable=="inherit") {
            tmp = tmp.parentElement;
        }
        if (tmp && tmp.contentEditable) return true;
    }
    return false;
}

function getAttributes(elem){
    var attributes = {}
    for (var att, i = 0, atts = elem.attributes, n = atts.length; i < n; i++){
        att = atts[i];
        attributes[att.nodeName] = att.nodeValue
    }
    return attributes
}

window.addEventListener("focus", function (e) {
    """+lrectconstruct+"""
    attributes = getAttributes(e.target)
    if (isKeyboardElement(e.target)) __kivy__keyboard_update(true, lrect, attributes);
}, true);

window.addEventListener("blur", function (e) {
    """+lrectconstruct+"""
    attributes = getAttributes(e.target)
    __kivy__keyboard_update(false, lrect, attributes);
}, true);

function __kivy__on_escape() {
    if (document.activeElement) {
        document.activeElement.blur();
    }
}
"""
            frame.ExecuteJavascript(jsCode)

    def OnLoadEnd(self, browser, frame, httpStatusCode):
        self.browser_widgets[browser].dispatch("on_load_end", frame, httpStatusCode)
        #largs[0].SetZoomLevel(2.0) # this works at this point

    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        self.browser_widgets[browser].dispatch("on_load_error", frame, errorCode, errorText, failedUrl)

    def OnRendererProcessTerminated(self, *largs):
        pass

    # RenderHandler

    def GetRootScreenRect(self, *largs):
        pass

    def GetViewRect(self, browser, rect):
        width, height = self.browser_widgets[browser].texture.size
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
        bw = self.browser_widgets[browser]
        bw.remove_widget(bw.popup)
        if shown:
            bw.add_widget(bw.popup)

    def OnPopupSize(self, browser, rect):
        bw = self.browser_widgets[browser]
        bw.popup.rpos = (rect[0], rect[1])
        bw.popup.size = (rect[2], rect[3])

    def OnPaint(self, browser, paintElementType, dirtyRects, buf, width, height):
        #print "ON PAINT", browser
        b = buf.GetString(mode="bgra", origin="top-left")
        bw = self.browser_widgets[browser]
        if paintElementType != cefpython.PET_VIEW:
            if bw.popup.texture.width*bw.popup.texture.height*4!=len(b):
                return True  # prevent segfault
            bw.popup.texture.blit_buffer(b, colorfmt='bgra', bufferfmt='ubyte')
            bw.popup.update_rect()
            return True
        if bw.texture.width*bw.texture.height*4!=len(b):
            return True  # prevent segfault
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

    def GetCookieManager(self, browser, mainUrl):
        cookie_manager = cefpython.CookieManager.GetGlobalManager()
        if cookie_manager:
            return cookie_manager
        else:
            print("No cookie manager found!")

    def OnProtocolExecution(self, *largs):
        pass

    # RessourceHandler


client_handler = ClientHandler()

def OnAfterCreated(browser, *largs):
    print "On After Created", browser, largs
    pw = None
    for key in client_handler.browser_widgets:
        print("ONAFTERCREATED", key)
        pw = client_handler.browser_widgets[key].parent
        if pw:
            break
    cb = CefBrowser(browser=browser)
    cb.pos = (0, 150)
    cb.size = (1024, 500)
    pw.add_widget(cb)
cefpython.SetGlobalClientCallback("OnAfterCreated", OnAfterCreated)


if __name__ == '__main__':
    import os
    from kivy.app import App
    from kivy.clock import Clock
    #from kivy.uix.behaviors import FocusBehavior
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    class CefBrowserApp(App):
        def timeout(self, *largs):
            cef_test_url = "file://"+os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.html")
            self.cb1.url = cef_test_url
            #self.cb1.keyboard_mode = "global"
        def build(self):
            class FocusButton(Button): # FocusBehavior, 
                pass

            ti1 = TextInput(text="ti1", pos=(0,700), size=(511, 50))
            ti2 = TextInput(text="ti2", pos=(513,700), size=(511, 50))
            fb1 = FocusButton(text="ti1", pos=(0,650), size=(511, 50))
            fb2 = FocusButton(text="ti2", pos=(513,650), size=(511, 50))
            self.cb1 = CefBrowser(url='http://jegger.ch/datapool/app/test_popup.html', pos=(0,0), size=(511, 650))
            self.cb2 = CefBrowser(url='http://jegger.ch/datapool/app/test_popup.html', keyboard_above_classes=["select2-input", ], pos=(513,0), size=(511, 650))
            # http://jegger.ch/datapool/app/test_popup.html
            # http://jegger.ch/datapool/app/test_events.html
            # https://rally1.rallydev.com/
            w = Widget()
            w.add_widget(self.cb1)
            w.add_widget(self.cb2)
            w.add_widget(fb1)
            w.add_widget(fb2)
            w.add_widget(ti1)
            w.add_widget(ti2)
            Clock.schedule_once(self.timeout, 10)
            return w

    CefBrowserApp().run()

    cefpython.Shutdown()

