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

from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.logger import Logger
from kivy.properties import *
from kivy.uix.widget import Widget
from lib.cefpython import cefpython
from cefkeyboard import CefKeyboardManager

import random

class CefBrowser(Widget):
    # Keyboard mode: "global" or "local".
    # 1. Global mode forwards keys to CEF all the time.
    # 2. Local mode forwards keys to CEF only when an editable
    #    control is focused (input type=text|password or textarea).
    url = StringProperty("about:blank")
    is_loading = BooleanProperty(False)
    can_go_back = BooleanProperty(False)
    can_go_forward = BooleanProperty(False)
    title = StringProperty("")
    browser = None
    popup = None
    popup_policy = None
    popup_handler = None
    close_handler = None
    __rect = None
    __js_bindings = None  # See bind_js()

    def __init__ (self, *largs, **dargs):
        self.url = dargs.pop("url", "about:blank")
        self.browser = dargs.pop("browser", None)
        self.popup = CefBrowserPopup(self)
        self.__rect = None
        self.__js_bindings = None
        super(CefBrowser, self).__init__(**dargs)

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
        self.browser.WasResized()
        self.bind(size=self.realign)
        self.bind(pos=self.realign)
        self.bind_js()

    def bind_js(self):
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
        else:
            self.__js_bindings.Rebind()

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
        if self.browser and value and value!=self.browser.GetUrl():
            print("ON URL", instance, value, self.browser.GetUrl(), self.browser.GetMainFrame().GetUrl())
            self.browser.Navigate(self.url)

    def on_js_dialog(self, browser, origin_url, accept_lang, dialog_type, message_text, default_prompt_text, callback,
                     suppress_message):
        pass

    def on_before_unload_dialog(self, browser, message_text, is_reload, callback):
        pass

    def on_certificate_error(self, err, url, cb):
        print("on_certificate_error", err, url)
        cb.Continue(False)

    def on_load_start(self, frame):
        pass

    def on_load_end(self, frame, httpStatusCode):
        pass

    def on_load_error(self, frame, errorCode, errorText, failedUrl):
        print("on_load_error=> Code: %s, errorText: %s, failedURL: %s" % (errorCode, errorText, failedUrl))
        pass

    __keyboard = None

    def keyboard_update(self, shown, rect, attributes):
        """
        :param shown: Show keyboard if true, hide if false (blur)
        :param rect: [x,y,width,height] of the input element
        :param attributes: Attributes of HTML element
        """
        if shown:
            self.request_keyboard(rect)
        else:
            self.release_keyboard()

    def request_keyboard(self, rect=None):
        print("REQUEST KB", rect)
        if not self.__keyboard:
            self.__keyboard = Window.request_keyboard(
                    self.release_keyboard, self)
            self.__keyboard.bind(on_key_down=self.on_key_down)
            self.__keyboard.bind(on_key_up=self.on_key_up)
        kw = self.__keyboard.widget
        if rect and len(rect)==4:
            kw.pos = (self.x+rect[0]+(rect[2]-kw.width)/2, self.y+self.height-rect[1]-rect[3]-kw.height)
        else:
            kw.pos = (self.x, self.y)
        CefKeyboardManager.reset_all_modifiers()

    def release_keyboard(self, *kwargs):
        print("RELEASE KB")
        CefKeyboardManager.reset_all_modifiers()
        if not self.__keyboard:
            return
        self.__keyboard.unbind(on_key_down=self.on_key_down)
        self.__keyboard.unbind(on_key_up=self.on_key_up)
        self.__keyboard.release()
        self.__keyboard = None

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
    pending_popups = {}

    def __init__(self, *largs):
        self.browser_widgets = {}

    # DisplayHandler TODO: OnContentsSizeChange, OnFaviconURLChange, OnNavStateChange

    def OnLoadingStateChange(self, browser, is_loading, can_go_back, can_go_forward):
        bw = self.browser_widgets[browser]
        bw.is_loading = is_loading
        bw.can_go_back = can_go_back
        bw.can_go_forward = can_go_forward
        if not is_loading:
            bw.bind_js()

    def OnAddressChange(self, browser, frame, url):
        if browser.GetMainFrame()==frame:
            self.browser_widgets[browser].url = url
        else:
            print("TODO: Address changed in Frame")

    def OnTitleChange(self, browser, new_title):
        self.browser_widgets[browser].title = new_title

    def OnTooltip(self, *largs):
        return True # We handled it. And did do nothing about it. :O

    def OnStatusMessage(self, browser, message):
        Logger.info("CefBrowser: Status: %s", message)

    def OnConsoleMessage(self, browser, message, source, line):
        Logger.info("CefBrowser: Console: %s - %s(%i)", message, source, line)
        return True # We handled it

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

    def OnBeforePopup(self, browser, frame, target_url, target_frame_name, popup_features, window_info, client, browser_settings, *largs):
        Logger.debug("CefBrowser: OnBeforePopup\n\tBrowser: %s\n\tFrame: %s\n\tURL: %s\n\tFrame Name: %s\n\tPopup Features: %s\n\tWindow Info: %s\n\tClient: %s\n\tBrowser Settings: %s\n\tRemaining Args: %s", browser, frame, target_url, target_frame_name, popup_features, window_info, client, browser_settings, largs)
        bw = self.browser_widgets[browser]
        if hasattr(bw.popup_policy, '__call__'):
            try:
                allow_popup = bw.popup_policy(bw, target_url)
                Logger.info("CefBrowser: Popup policy handler "+("allowed" if allow_popup else "blocked")+" popup")
            except Exception as err:
                Logger.warning("CefBrowser: Popup policy handler failed with error:", err)
                allow_popup = False
        else:
            Logger.info("CefBrowser: No Popup policy handler detected. Default is block.")
            allow_popup = False
        if allow_popup:
            r = random.randint(1, 2**31-1)
            wi = cefpython.WindowInfo()
            wi.SetAsChild(0)
            wi.SetAsOffscreen(r)
            window_info.append(wi)
            browser_settings.append({})
            self.pending_popups[r] = browser
            return False
        else:
            return True

    def RunModal(self, browser, *largs):
        Logger.debug("CefBrowser: RunModal\n\tBrowser: %s\n\tRemaining Args: %s", browser, largs)
        return False

    def DoClose(self, browser):
        bw = self.browser_widgets[browser]
        bw.release_keyboard()
        if hasattr(bw.close_handler, '__call__'):
            try:
                bw.close_handler(bw)
            except Exception as err:
                Logger.warning("CefBrowser: Close handler failed with error: %s", err)
        try:
            bw.parent.remove_widget(bw)
        except:
            pass
        del self.browser_widgets[browser]
        return False

    def OnBeforeClose(self, browser, *largs):
        print("On Before Close")

    # LoadHandler

    def OnLoadStart(self, browser, frame):
        bw = self.browser_widgets[browser]
        bw.dispatch("on_load_start", frame)
        if bw:
            bw.browser.SendFocusEvent(True)
            lrectconstruct = ""
            if not frame.GetParent():
                lrectconstruct = """try {
    var rect = elem.getBoundingClientRect();
    var lrect = [rect.left, rect.top, rect.width, rect.height];
} catch (err) {}"""
            jsCode = """
window.print = function () {
    console.log("Print dialog blocked");
};

var __kivy__activeKeyboardElement = false;
var __kivy__updateRectTimer = false;
var __kivy__lastRect = [];

function __kivy__isKeyboardElement(elem) {
    try {
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
    } catch (err) {}
    return false;
}

function __kivy__getAttributes(elem) {
    var attributes = {};
    for (var att, i = 0, atts = elem.attributes, n = atts.length; i < n; i++) {
        att = atts[i];
        attributes[att.nodeName] = att.nodeValue;
    }
    return attributes;
}

function __kivy__getRect(elem) {
    var lrect = [];
    """+lrectconstruct+"""
    return lrect;
}

window.addEventListener("focus", function (e) {
    var lrect = __kivy__getRect(e.target);
    var attributes = __kivy__getAttributes(e.target);
    var ike = __kivy__isKeyboardElement(e.target);
    console.log("focus "+e.target.toString()+JSON.stringify(attributes)+JSON.stringify(ike));
    __kivy__keyboard_update(ike, lrect, attributes);
    __kivy__activeKeyboardElement = (ike?e.target:false);
    __kivy__lastRect = lrect;
}, true);

window.addEventListener("blur", function (e) {
    var lrect = __kivy__getRect(e.target);
    var attributes = __kivy__getAttributes(e.target);
    console.log("blur "+e.target.toString()+JSON.stringify(attributes));
    __kivy__keyboard_update(false, lrect, attributes);
    __kivy__activeKeyboardElement = false;
    __kivy__lastRect = [];
}, true);

function __kivy__updateRect() {
    if (__kivy__updateRectTimer) window.clearTimeout(__kivy__updateRectTimer);
    if (__kivy__activeKeyboardElement) {
        var lrect = __kivy__getRect(__kivy__activeKeyboardElement);
        if (!(__kivy__lastRect && lrect.length==4 && __kivy__lastRect.length==4 && lrect[0]==__kivy__lastRect[0] && lrect[1]==__kivy__lastRect[1] && lrect[2]==__kivy__lastRect[2] && lrect[3]==__kivy__lastRect[3])) {
            __kivy__keyboard_update(true, lrect, false);
            __kivy__lastRect = lrect;
        }
    }
    __kivy__updateRectTimer = window.setTimeout(__kivy__updateRect, 1000);
}
window.addEventListener("scroll", function (e) {
    if (__kivy__updateRectTimer) window.clearTimeout(__kivy__updateRectTimer);
    __kivy__updateRectTimer = window.setTimeout(__kivy__updateRect, 25);
}, true);

function __kivy__on_escape() {
    if (__kivy__activeKeyboardElement) __kivy__activeKeyboardElement.blur();
    if (document.activeElement) document.activeElement.blur();
}
var ae = document.activeElement;
if (ae) {
    ae.blur();
    ae.focus();
}
__kivy__updateRectTimer = window.setTimeout(__kivy__updateRect, 1000);
"""
            frame.ExecuteJavascript(jsCode)

    def OnLoadEnd(self, browser, frame, httpStatusCode):
        bw = self.browser_widgets[browser]
        bw.dispatch("on_load_end", frame, httpStatusCode)
        #browser.SetZoomLevel(2.0) # this works at this point

    def OnLoadError(self, browser, frame, errorCode, errorText, failedUrl):
        bw = self.browser_widgets[browser]
        bw.dispatch("on_load_error", frame, errorCode, errorText, failedUrl)

    def OnRendererProcessTerminated(self, *largs):
        print("OnRendererProcessTerminated", largs)

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
        #print("ON PAINT", browser)
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

    def OnBeforeBrowse(self, browser, frame, request, isRedirect):
        frame.ExecuteJavascript("try {__kivy__on_escape();} catch (err) {}")

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

def OnAfterCreated(browser):
    print("On After Created", browser, browser.IsPopup(), browser.GetIdentifier(), browser.GetWindowHandle(), browser.GetOpenerWindowHandle())
    if browser.IsPopup():
        wh = browser.GetWindowHandle()
        cb = CefBrowser(browser=browser)
        bw = False
        if wh in client_handler.pending_popups:
            parent_browser = client_handler.pending_popups[wh]
            if parent_browser in client_handler.browser_widgets:
                bw = client_handler.browser_widgets[parent_browser]
        if not bw:
            bw = client_handler.browser_widgets[client_handler.browser_widgets.iterkeys().next()]
        if hasattr(bw.popup_handler, '__call__'):
            try:
                bw.popup_handler(bw, cb)
            except Exception as err:
                Logger.warning("CefBrowser: Popup handler failed with error: %s", err)
        else:
            Logger.info("CefBrowser: No Popup handler detected.")
        if not cb.parent:
            Logger.warning("CefBrowser: Popup handler did not add the popup_browser to the widget tree. Adding it to Window.")
            Window.add_widget(cb)
cefpython.SetGlobalClientCallback("OnAfterCreated", OnAfterCreated)

def OnCertificateError(self, err, url, cb):
    print("OnCertificateError", err, url, cb)
    # Check if cert verification is disabled
    if os.path.isfile("/etc/rentouch/ssl-verification-disabled"):
        cb.Continue(True)
    #.dispatch("on_certificate_error", err, url, cb)
cefpython.SetGlobalClientCallback("OnCertificateError", OnCertificateError)

if __name__ == '__main__':
    import os
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.behaviors import FocusBehavior
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    class CefBrowserApp(App):
        def timeout(self, *largs):
            cef_test_url = "file://"+os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.html")
            self.cb1.url = cef_test_url
        def build(self):
            class FocusButton(FocusBehavior, Button):
                pass
            wid = Window.width/2
            hei = Window.height
            ti1 = TextInput(text="ti1", pos=(0,hei-50), size=(wid-1, 50))
            ti2 = TextInput(text="ti2", pos=(wid+1,hei-50), size=(wid-1, 50))
            fb1 = FocusButton(text="ti1", pos=(0,hei-100), size=(wid-1, 50))
            fb2 = FocusButton(text="ti2", pos=(wid+1,hei-100), size=(wid-1, 50))
            def url_handler(self, url):
                print("URL HANDLER", url)
            def title_handler(self, title):
                print("TITLE HANDLER", title)
            def close_handler(self):
                print("CLOSE HANDLER")
            def popup_policy_handler(self, popup_url):
                print("POPUP POLICY HANDLER", popup_url)
                return True
            def popup_handler(self, popup_browser):
                print("POPUP HANDLER", popup_browser)
                pw = None
                for key in client_handler.browser_widgets:
                    pw = client_handler.browser_widgets[key].parent
                    if pw:
                        break
                popup_browser.pos = (Window.width/4, Window.height/4)
                popup_browser.size = (Window.width/2, Window.height/2)
                popup_browser.popup_handler = popup_handler
                popup_browser.close_handler = close_handler
                pw.add_widget(popup_browser)
            self.cb1 = CefBrowser(url='http://jegger.ch/datapool/app/test_popup.html', pos=(0,0), size=(wid-1, hei-100))
            self.cb1.popup_policy = popup_policy_handler
            self.cb1.popup_handler = popup_handler
            self.cb1.close_handler = close_handler
            self.cb1.bind(url=url_handler)
            self.cb1.bind(title=title_handler)
            self.cb2 = CefBrowser(url='http://jegger.ch/datapool/app/test_popup.html', pos=(wid+1,0), size=(wid-1, hei-100))
            self.cb2.popup_policy = popup_policy_handler
            self.cb2.popup_handler = popup_handler
            self.cb2.close_handler = close_handler
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

