#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
The CEFBrowser Widget actually displays the browser. It displays ONLY the
browser. If you need controls or tabs, check out the `examples`
"""

__all__ = ("CEFBrowser")

from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.graphics.texture import Texture
from kivy.factory import Factory
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import *
from kivy.uix.behaviors import FocusBehavior
from kivy.uix.widget import Widget
from lib.cefpython import cefpython, cefpython_initialize
from cefkeyboard import CEFKeyboardManager

import json
import os
import random
import time


Builder.load_file(os.path.join(os.path.realpath(os.path.dirname(__file__)), "cefbrowser.kv"))
cef_browser_js_alert = Factory.CEFBrowserJSAlert()
cef_browser_js_confirm = Factory.CEFBrowserJSConfirm()
cef_browser_js_prompt = Factory.CEFBrowserJSPrompt()

class CEFAlreadyInitialized(Exception):
    pass

class CEFBrowser(Widget, FocusBehavior):
    """Displays a Browser"""
    # Class Variables
    certificate_error_handler = None
    """The value of the `certificate_error_handler` class variable is a
    function that handles certificate errors.
    It takes 2 arguments:
    - `err`: The certificate error number that occurred
    - `url`: The URL that was to be loaded
    It should return a bool that indicates whether to ignore the error or not:
    - True: Ignore warning - False: Abort loading
    If `certificate_error_handler` is None or cannot be executed, the default
    is False."""
    _cefpython_initialized = False
    _command_line_switches = {}
    _settings = {}
    _caches_path = None
    _cookies_path = None
    _logs_path = None
    _cookie_manager = None
    
    # Instance Variables
    url = StringProperty("about:blank")
    """The URL of the (main frame of the) browser."""
    is_loading = BooleanProperty(False)
    """Whether the browser is loading content"""
    can_go_back = BooleanProperty(False)
    """Whether the browser gan go back in history at this time"""
    can_go_forward = BooleanProperty(False)
    """Whether the browser gan go forward in history at this time"""
    title = StringProperty("")
    """The title of the currently displayed content (e.g. for tab/window title)"""
    popup_policy = None
    """The value of the `popup_policy` variable is a function that handles
    the policy whether to allow or block popups.
    It takes 2 arguments:
    - `browser`: The browser which wants to open the popup
    - `url`: The URL of the (future) popup
    It should return a bool that indicates whether to open the popup or not:
    - True: Allow popup - False: Block popup
    If `popup_policy` is None or cannot be executed, the default is False."""
    popup_handler = None
    """The value of the `popup_handler` variable is a function that handles
    newly created popups.
    It takes 2 arguments:
    - `browser`: The browser which opened the popup
    - `popup_browser`: The (newly created) popup browser
    It should place the `popup_browser` somewhere in the widget tree
    If `popup_handler` is None, cannot be executed or doesn't insert
    `popup_browser` to the widget tree, the default is to add it to the Window."""
    close_handler = None
    """The value of the `close_handler` variable is a function that handles
    closing browsers or popups.
    It takes 1 argument:
    - `browser`: The browser to be closed
    It remove everything belonging to `browser` from the widget tree
    If `close_handler` is None, cannot be executed or doesn't remove `browser`
    from the widget tree, the default is to just remove the `browser` from its
    parent."""
    keyboard_position = None
    """The value of the `keyboard_position` variable is a function that handles
    positioning of the keyboard on focusing a keyboard element in the browser.
    It takes 1 argument:
    - `browser`: The browser in which the element was focused
    - `keyboard_widget`: The keyboard widget
    - `rect`: The rectangle the focused element takes *within* the browser
    - `attributes`: The HTML attributes of the focused element
    It should set `keyboard_widget.pos` to the desired value
    If `close_handler` is None, cannot be executed or doesn't remove `browser`
    from the widget tree, the default is to just leave the keyboard widget
    where it is."""
    _touches = []
    _browser = None
    _popup = None
    _texture = None
    __rect = None
    __keyboard_state = {}

    def __init__(self, url="about:blank", *largs, **dargs):
        self.url = url
        self.popup_policy = dargs.pop("popup_policy", CEFBrowser.always_block_popups)
        self.popup_handler = dargs.pop("popup_handler", CEFBrowser.fullscreen_popup)
        self.close_handler = dargs.pop("close_handler", CEFBrowser.do_nothing)
        self.keyboard_position = dargs.pop("keyboard_position", CEFBrowser.keyboard_position_optimal)
        self.js = CEFBrowserJSProxy(self)
        self._browser = dargs.pop("browser", None)
        self._popup = CEFBrowserPopup(self)
        self.__rect = None
        super(CEFBrowser, self).__init__(**dargs)

        self.register_event_type("on_load_start")
        self.register_event_type("on_load_end")
        self.register_event_type("on_load_error")
        self.register_event_type("on_js_dialog")
        self.register_event_type("on_before_unload_dialog")

        self._texture = Texture.create(size=self.size, colorfmt="rgba", bufferfmt="ubyte")
        self._texture.flip_vertical()
        with self.canvas:
            Color(1, 1, 1)
            self.__rect = Rectangle(pos=self.pos, size=self.size, texture=self._texture)

        if not CEFBrowser._cefpython_initialized:
            cefpython_initialize(CEFBrowser)
            CEFBrowser._cefpython_initialized = True
        if not self._browser:
            windowInfo = cefpython.WindowInfo()
            windowInfo.SetAsOffscreen(0)
            self._browser = cefpython.CreateBrowserSync(windowInfo, {}, navigateUrl=self.url)
        self._browser.SetClientHandler(client_handler)
        client_handler.browser_widgets[self._browser] = self
        self._browser.WasResized()
        self.bind(size=self._realign)
        self.bind(pos=self._realign)
        self.bind(parent=self._on_parent)
        self.bind(focus=self._on_focus)
        self.js._inject()

    @classmethod
    def update_command_line_switches(cls, d):
        """ Updates the command line switches for cefpython with the options given in the dict `d`.
        For possible keys and values, see the cefpython docs."""
        if CEFBrowser._cefpython_initialized:
            raise CEFAlreadyInitialized()
        CEFBrowser._command_line_switches.update(d)
        Logger.debug("CEFBrowser: update_command_line_switches => %s", CEFBrowser._command_line_switches)
        print "update_command_line_switches", cls._command_line_switches

    @classmethod
    def update_settings(cls, d):
        """ Updates the settings for cefpython with the options given in the dict `d`.
        For possible keys and values, see the cefpython docs."""
        if CEFBrowser._cefpython_initialized:
            raise CEFAlreadyInitialized()
        CEFBrowser._settings.update(d)
        Logger.debug("CEFBrowser: update_settings => %s", CEFBrowser._settings)

    @classmethod
    def set_caches_path(cls, cp):
        """ The string `cp` is the path to a read- and writeable location where CEF can store its run-time caches."""
        if CEFBrowser._cefpython_initialized:
            raise CEFAlreadyInitialized()
        CEFBrowser._caches_path = cp
        Logger.debug("CEFBrowser: caches_path: %s\n cookies_path: %s\n logs_path: %s", CEFBrowser._caches_path, CEFBrowser._cookies_path, CEFBrowser._logs_path)

    @classmethod
    def set_cookies_path(cls, cp):
        """ The string `cp` is the path to a read- and writeable location where CEF can store its run-time cookies."""
        if CEFBrowser._cefpython_initialized:
            raise CEFAlreadyInitialized()
        CEFBrowser._cookies_path = cp
        Logger.debug("CEFBrowser: caches_path: %s\n cookies_path: %s\n logs_path: %s", CEFBrowser._caches_path, CEFBrowser._cookies_path, CEFBrowser._logs_path)

    @classmethod
    def set_logs_path(cls, lp):
        """ The string `lp` is the path to a read- and writeable location where CEF can write its log."""
        if CEFBrowser._cefpython_initialized:
            raise CEFAlreadyInitialized()
        CEFBrowser._logs_path = lp
        Logger.debug("CEFBrowser: caches_path: %s\n cookies_path: %s\n logs_path: %s", CEFBrowser._caches_path, CEFBrowser._cookies_path, CEFBrowser._logs_path)

    @classmethod
    def set_data_path(cls, dp):
        """ The string `dp` class variable is the path to a read- and writeable location where CEF can write its run-time data:
        - caches to '`dp`/cache'
        - cookies to '`dp`/cookies'
        - logs to '`dp`/logs'
        """
        if CEFBrowser._cefpython_initialized:
            raise CEFAlreadyInitialized()
        if not os.path.isdir(dp):
            os.mkdir(dp, 0700)
        CEFBrowser._caches_path = os.path.join(dp, "caches")
        CEFBrowser._cookies_path = os.path.join(dp, "cookies")
        CEFBrowser._logs_path = os.path.join(dp, "logs")
        Logger.debug("CEFBrowser: \ncaches_path: %s\n cookies_path: %s\n logs_path: %s", CEFBrowser._caches_path, CEFBrowser._cookies_path, CEFBrowser._logs_path)

    def _realign(self, *largs):
        ts = self._texture.size
        ss = self.size
        schg = (ts[0]!=ss[0] or ts[1]!=ss[1])
        if schg:
            self._texture = Texture.create(size=self.size, colorfmt="rgba", bufferfmt="ubyte")
            self._texture.flip_vertical()
        if self.__rect:
            with self.canvas:
                Color(1, 1, 1)
                self.__rect.pos = self.pos
                if schg:
                    self.__rect.size = self.size
            if schg:
                self._update_rect()
        if self._browser:
            self._browser.WasResized()
            self._browser.NotifyScreenInfoChanged()
        try:
            self._keyboard_update(**self.__keyboard_state)
        except:
            pass

    def _on_parent(self, obj, parent):
        print "_on_parent", parent, self.__keyboard_state
        try:
            self._keyboard_update(**self.__keyboard_state)
        except:
            pass

    def _on_focus(self, obj, focus):
        super(CEFBrowser, self)._on_focus(obj, focus)
        if not focus and self.__keyboard_state["shown"]:
            self._browser.GetMainFrame().ExecuteJavascript("__kivy__activeKeyboardElement.blur();")

    def _update_rect(self):
        if self.__rect:
            self.__rect.texture = self._texture

    def go_back(self):
        self._browser.GoBack()

    def go_forward(self):
        self._browser.GoForward()

    def stop_loading(self):
        self._browser.StopLoad()

    def reload(self, ignore_cache=True):
        if ignore_cache:
            self._browser.ReloadIgnoreCache()
        else:
            self._browser.Reload()

    def delete_cookie(self, url=""):
        """ Deletes the cookie with the given url. If url is empty all cookies get deleted.
        """
        cookie_manager = cefpython.CookieManager.GetGlobalManager()
        if cookie_manager:
            cookie_manager.DeleteCookies(url, "")
        else:
            print("No cookie manager found!, Can't delete cookie(s)")

    def on_url(self, instance, value):
        if self._browser and value and value!=self._browser.GetUrl():
            print("ON URL", instance, value, self._browser.GetUrl(), self._browser.GetMainFrame().GetUrl())
            self._browser.Navigate(self.url)

    def on_js_dialog(self, browser, origin_url, accept_lang, dialog_type, message_text, default_prompt_text, callback,
                     suppress_message):
        pass

    def on_before_unload_dialog(self, browser, message_text, is_reload, callback):
        pass

    def on_load_start(self, frame):
        pass

    def on_load_end(self, frame, httpStatusCode):
        pass

    def on_load_error(self, frame, errorCode, errorText, failedUrl):
        print("on_load_error=> Code: %s, errorText: %s, failedURL: %s" % (errorCode, errorText, failedUrl))
        pass

    def _keyboard_update(self, shown, rect, attributes):
        """
        :param shown: Show keyboard if true, hide if false (blur)
        :param rect: [x,y,width,height] of the input element
        :param attributes: Attributes of HTML element
        """
        self.__keyboard_state = {"shown":shown, "rect":rect, "attributes":attributes}
        print("KB", self, self.__keyboard_state, self.parent, rect, attributes)
        if shown and self.parent: # No orphaned keyboards
            self.focus = True
            self.keyboard_position(self, self.keyboard.widget, rect, attributes)
        else:
            self.focus = False
        # CEFKeyboardManager.reset_all_modifiers() # TODO: necessary?

    @classmethod
    def keyboard_position_simple(cls, browser, keyboard_widget, rect, attributes):
        if not keyboard_widget.docked:
            if rect and len(rect)==4:
                keyboard_widget.pos = (browser.x+rect[0]+(rect[2]-keyboard_widget.width)/2, browser.y+browser.height-rect[1]-rect[3]-keyboard_widget.height)
            else:
                keyboard_widget.pos = (browser.x, browser.y)

    @classmethod
    def keyboard_position_optimal(cls, browser, keyboard_widget, rect, attributes): # TODO: place right, left, etc. see cefkivy
        if not keyboard_widget.docked:
            cls.keyboard_position_simple(browser, keyboard_widget, rect, attributes)
            if Window.width<keyboard_widget.x+keyboard_widget.width:
                keyboard_widget.x = Window.width-keyboard_widget.width
            if keyboard_widget.x<0:
                keyboard_widget.x = 0
            if Window.height<keyboard_widget.y+keyboard_widget.height:
                keyboard_widget.y = Window.height-keyboard_widget.height
            if keyboard_widget.y<0:
                keyboard_widget.y = 0

    @classmethod
    def always_allow_popups(cls, browser, url):
        return True

    @classmethod
    def always_block_popups(cls, browser, url):
        return True

    @classmethod
    def fullscreen_popup(cls, browser, popup_browser):
        Window.add_widget(popup_browser)

    @classmethod
    def do_nothing(cls, browser):
        pass

    @classmethod
    def allow_invalid_certificates(cls, browser, err, url):
        """
        `browser` is a dummy argument, because python treats class variables
        containing a function as unbound class methods
        """
        return True

    @classmethod
    def block_invalid_certificates(cls, browser, err, url):
        """
        `browser` is a dummy argument, because python treats class variables
        containing a function as unbound class methods
        """
        return False

    def keyboard_on_key_down(self, *largs):
        print("KEY DOWN", largs)
        CEFKeyboardManager.kivy_on_key_down(self._browser, *largs)

    def keyboard_on_key_up(self, *largs):
        print("KEY UP", largs)
        CEFKeyboardManager.kivy_on_key_up(self._browser, *largs)

    def on_touch_down(self, touch, *kwargs):
        if not self.collide_point(*touch.pos):
            return

        # Do not support more than two touches!
        if len(self._touches) > 2:
            return

        touch.is_dragging = False
        touch.is_scrolling = False
        touch.is_right_click = False
        self._touches.append(touch)
        touch.grab(self)

        return True

    def on_touch_move(self, touch, *kwargs):
        if touch.grab_current is not self:
            return

        x = touch.x - self.pos[0]
        y = self.height-touch.y + self.pos[1]

        x_start = touch.opos[0] - self.pos[0]
        y_start = self.height-touch.opos[1] + self.pos[1]

        if len(self._touches) == 1:
            if not touch.is_scrolling or touch.is_right_click:
                # Dragging
                if (abs(touch.dx) > 5 or abs(touch.dy) > 5) or touch.is_dragging:
                    if touch.is_dragging:
                        self._browser.SendMouseMoveEvent(
                            x, y, 16, mouseLeave=False
                        )
                    else:
                        self._browser.SendMouseClickEvent(
                            x_start, y_start, 0, cefpython.MOUSEBUTTON_LEFT,
                            mouseUp=False, clickCount=1
                        )
                        print("Mouse down")
                        touch.is_dragging = True

        elif len(self._touches) == 2:
            # Scroll only if a minimal distance passed (could be right click)
            touch1, touch2 = self._touches[:2]
            dx = touch2.dx / 2. + touch1.dx / 2.
            dy = touch2.dy / 2. + touch1.dy / 2.
            if (abs(dx) > 5 or abs(dy) > 5) or touch.is_scrolling:
                # Check all touches for a certain state
                for _touch in self._touches:
                    if _touch.is_dragging:
                        # End the drag event by releasing the mouse button
                        self._browser.SendMouseClickEvent(
                            _touch.ppos[0], _touch.ppos[1], 0,
                            cefpython.MOUSEBUTTON_LEFT, mouseUp=True,
                            clickCount=1
                        )
                        print("Mouse up")
                        _touch.is_dragging = False
                    # Set touch state to scrolling
                    _touch.is_scrolling = True
                self._browser.SendMouseWheelEvent(
                    touch.x, self.height-touch.pos[1], 0, dx, -dy
                )
                print("Mouse scroll")
        return True

    def on_touch_up(self, touch, *kwargs):
        if touch.grab_current is not self:
            return

        y = self.height-touch.pos[1] + self.pos[1]
        x = touch.x - self.pos[0]

        if len(self._touches) == 2:
            if not touch.is_scrolling:
                # Right click (mouse down, mouse up)
                self._touches[0].is_right_click = self._touches[1].is_right_click = True
                self._browser.SendMouseClickEvent(
                    x, y, 0, cefpython.MOUSEBUTTON_RIGHT,
                    mouseUp=False, clickCount=1
                )
                self._browser.SendMouseClickEvent(
                    x, y, 0, cefpython.MOUSEBUTTON_RIGHT,
                    mouseUp=True, clickCount=1
                )
                print("Mouse right click")
        else:
            if touch.is_dragging:
                # Drag end (mouse up)
                self._browser.SendMouseClickEvent(
                    touch.ppos[0], self.height-touch.ppos[1] + self.pos[1], 0,
                    cefpython.MOUSEBUTTON_LEFT,
                    mouseUp=True, clickCount=1
                )
                print("Mouse up (end of drag)")
            elif not touch.is_right_click and not touch.is_scrolling:
                # Left click (mouse down, mouse up)
                count = 1
                if touch.is_double_tap:
                    count = 2
                self._browser.SendMouseClickEvent(
                    x, y, 0, 
                    cefpython.MOUSEBUTTON_LEFT,
                    mouseUp=False, clickCount=count
                )
                self._browser.SendMouseClickEvent(
                    x, y, 0, 
                    cefpython.MOUSEBUTTON_LEFT,
                    mouseUp=True, clickCount=count
                )
                print("Mouse click")

        self._touches.remove(touch)
        touch.ungrab(self)
        return True


class CEFBrowserPopup(Widget):
    rx = NumericProperty(0)
    ry = NumericProperty(0)
    rpos = ReferenceListProperty(rx, ry)

    def __init__(self, browser_widget, *largs, **dargs):
        super(CEFBrowserPopup, self).__init__()
        self.browser_widget = browser_widget
        self.__rect = None
        self._texture = Texture.create(size=self.size, colorfmt="rgba", bufferfmt="ubyte")
        self._texture.flip_vertical()
        with self.canvas:
            Color(1, 1, 1)
            self.__rect = Rectangle(pos=self.pos, size=self.size, texture=self._texture)
        self.bind(rpos=self._realign)
        self.bind(size=self._realign)
        browser_widget.bind(pos=self._realign)
        browser_widget.bind(size=self._realign)

    def _realign(self, *largs):
        self.x = self.rx+self.browser_widget.x
        self.y = self.browser_widget.height-self.ry-self.height+self.browser_widget.y
        ts = self._texture.size
        ss = self.size
        schg = (ts[0]!=ss[0] or ts[1]!=ss[1])
        if schg:
            self._texture = Texture.create(size=self.size, colorfmt="rgba", bufferfmt="ubyte")
            self._texture.flip_vertical()
        if self.__rect:
            with self.canvas:
                Color(1, 1, 1)
                self.__rect.pos = self.pos
                if schg:
                    self.__rect.size = self.size
            if schg:
                self._update_rect()

    def _update_rect(self):
        if self.__rect:
            self.__rect.texture = self._texture


class CEFBrowserJSFunctionProxy():
    def __init__(self, browser_widget, key, *largs):
        self.browser_widget = browser_widget
        self.key = key
    
    def __call__(self, *largs):
        js_code = str(self.key)+"("
        first = True
        for arg in largs:
            if not first:
                js_code += ", "
            js_code += json.dumps(arg)
            first = False
        js_code += ");"
        frame = self.browser_widget._browser.GetMainFrame()
        frame.ExecuteJavascript(js_code)

class CEFBrowserJSProxy():
    def __init__(self, browser_widget, *largs):
        self.browser_widget = browser_widget
        self.__js_bindings_dict = {"__kivy__keyboard_update":browser_widget._keyboard_update}
        self.__js_bindings = None
    
    def _inject(self):
        # When browser.Navigate() is called, some bug appears in CEF
        # that makes CefRenderProcessHandler::OnBrowserDestroyed()
        # is being called. This destroys the javascript bindings in
        # the Render process. We have to make the js bindings again,
        # after the call to Navigate() when OnLoadingStateChange()
        # is called with isLoading=False. Problem reported here:
        # http://www.magpcss.org/ceforum/viewtopic.php?f=6&t=11009
        if not self.__js_bindings:
            self.__js_bindings = cefpython.JavascriptBindings(bindToFrames=True, bindToPopups=True)
            for k in self.__js_bindings_dict:
                self.__js_bindings.SetFunction(k, self.__js_bindings_dict[k])
            self.browser_widget._browser.SetJavascriptBindings(self.__js_bindings)
        else:
            self.__js_bindings.Rebind()
    
    def bind(self, **dargs):
        self.__js_bindings_dict.update(dargs)
        self.__js_bindings = None
        self._inject()
    
    def __getattr__(self, key):
        print "getattr", key
        return CEFBrowserJSFunctionProxy(self.browser_widget, key)


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
            bw.js._inject()

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
        Logger.info("CEFBrowser: Status: %s", message)

    def OnConsoleMessage(self, browser, message, source, line):
        Logger.info("CEFBrowser: Console: %s - %s(%i)", message, source, line)
        return True # We handled it

    # DownloadHandler

    # DragHandler

    # JavascriptContextHandler

    # JavascriptDialogHandler
    active_js_dialog = None

    def OnJavascriptDialog(self, browser, origin_url, accept_lang, dialog_type, message_text, default_prompt_text, callback, suppress_message, *largs):
        dialog_types = {
            cefpython.JSDIALOGTYPE_ALERT:["alert", cef_browser_js_alert],
            cefpython.JSDIALOGTYPE_CONFIRM:["confirm", cef_browser_js_confirm],
            cefpython.JSDIALOGTYPE_PROMPT:["prompt", cef_browser_js_prompt],
        }
        print("OnJavascriptDialog", browser, origin_url, accept_lang, dialog_types[dialog_type][0], message_text, default_prompt_text, callback, suppress_message, largs)
        def js_continue(allow, user_input):
            active_js_dialog = None
            callback.Continue(allow, user_input)
        p = dialog_types[dialog_type][1]
        p.text = message_text
        p.js_continue = js_continue
        p.default_prompt_text = default_prompt_text
        p.open()
        active_js_dialog = p
        return True

    def OnBeforeUnloadJavascriptDialog(self, browser, message_text, is_reload, callback):
        def js_continue(allow, user_input):
            active_js_dialog = None
            callback.Continue(allow, user_input)
        p = cef_browser_js_confirm
        p.text = message_text
        p.js_continue = js_continue
        p.default_prompt_text = ""
        p.open()
        active_js_dialog = p
        return True

    def OnResetJavascriptDialogState(self, browser):
        if active_js_dialog:
            active_js_dialog.dismiss()

    # KeyboardHandler

    def OnPreKeyEvent(self, *largs):
        pass

    def OnKeyEvent(self, *largs):
        pass

    # LifeSpanHandler

    def OnBeforePopup(self, browser, frame, target_url, target_frame_name, popup_features, window_info, client, browser_settings, *largs):
        Logger.debug("CEFBrowser: OnBeforePopup\n\tBrowser: %s\n\tFrame: %s\n\tURL: %s\n\tFrame Name: %s\n\tPopup Features: %s\n\tWindow Info: %s\n\tClient: %s\n\tBrowser Settings: %s\n\tRemaining Args: %s", browser, frame, target_url, target_frame_name, popup_features, window_info, client, browser_settings, largs)
        bw = self.browser_widgets[browser]
        if hasattr(bw.popup_policy, "__call__"):
            try:
                allow_popup = bw.popup_policy(bw, target_url)
                Logger.info("CEFBrowser: Popup policy handler "+("allowed" if allow_popup else "blocked")+" popup")
            except Exception as err:
                Logger.warning("CEFBrowser: Popup policy handler failed with error:", err)
                allow_popup = False
        else:
            Logger.info("CEFBrowser: No Popup policy handler detected. Default is block.")
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
        Logger.debug("CEFBrowser: RunModal\n\tBrowser: %s\n\tRemaining Args: %s", browser, largs)
        return False

    def DoClose(self, browser):
        bw = self.browser_widgets[browser]
        bw.focus = False
        if hasattr(bw.close_handler, "__call__"):
            try:
                bw.close_handler(bw)
            except Exception as err:
                Logger.warning("CEFBrowser: Close handler failed with error: %s", err)
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
        bw.focus = False
        if bw:
            bw._browser.SendFocusEvent(True)
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
    var w = window;
    var lrect = [0,0,0,0];
    while (elem && w) {
        try {
            var rect = elem.getBoundingClientRect();
            console.log(rect.left+", "+rect.top+", "+rect.width+", "+rect.height);
            lrect[0] += rect.left;
            lrect[1] += rect.top;
            if (lrect[2]==0) lrect[2] = rect.width;
            if (lrect[3]==0) lrect[3] = rect.height;
            elem = w.frameElement;
            w = w.parent;
        } catch (err) {
            console.log(err.toString());
            elem = false;
        }
    }
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
        width, height = self.browser_widgets[browser]._texture.size
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
        bw.remove_widget(bw._popup)
        if shown:
            bw.add_widget(bw._popup)

    def OnPopupSize(self, browser, rect):
        bw = self.browser_widgets[browser]
        bw._popup.rpos = (rect[0], rect[1])
        bw._popup.size = (rect[2], rect[3])

    def OnPaint(self, browser, paintElementType, dirtyRects, buf, width, height):
        #print("ON PAINT", browser, time.time())
        b = buf.GetString(mode="bgra", origin="top-left")
        bw = self.browser_widgets[browser]
        if paintElementType != cefpython.PET_VIEW:
            if bw._popup._texture.width*bw._popup._texture.height*4!=len(b):
                return True  # prevent segfault
            bw._popup._texture.blit_buffer(b, colorfmt="bgra", bufferfmt="ubyte")
            bw._popup._update_rect()
            return True
        if bw._texture.width*bw._texture.height*4!=len(b):
            return True  # prevent segfault
        bw._texture.blit_buffer(b, colorfmt="bgra", bufferfmt="ubyte")
        bw._update_rect()
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
        cb = CEFBrowser(browser=browser)
        bw = False
        if wh in client_handler.pending_popups:
            parent_browser = client_handler.pending_popups[wh]
            if parent_browser in client_handler.browser_widgets:
                bw = client_handler.browser_widgets[parent_browser]
        if not bw:
            bw = client_handler.browser_widgets[client_handler.browser_widgets.iterkeys().next()]
        if hasattr(bw.popup_handler, "__call__"):
            try:
                bw.popup_handler(bw, cb)
            except Exception as err:
                Logger.warning("CEFBrowser: Popup handler failed with error: %s", err)
        else:
            Logger.info("CEFBrowser: No Popup handler detected.")
        if not cb.parent:
            Logger.warning("CEFBrowser: Popup handler did not add the popup_browser to the widget tree. Adding it to Window.")
            Window.add_widget(cb)
cefpython.SetGlobalClientCallback("OnAfterCreated", OnAfterCreated)

def OnCertificateError(err, url, cb):
    print("OnCertificateError", err, url, cb)
    if CEFBrowser.certificate_error_handler:
        try:
            res = CEFBrowser.certificate_error_handler(CEFBrowser(), err, url)
            if res:
                cb.Continue(True)
                return
        except Exception as err:
            Logger.warning("CEFBrowser: Error in certificate error handler.\n%s", err)
cefpython.SetGlobalClientCallback("OnCertificateError", OnCertificateError)

if __name__ == "__main__":
    import os
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.uix.button import Button
    from kivy.uix.textinput import TextInput
    cef_test_url = "file://"+os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.html")
    class CEFBrowserApp(App):
        def timeout(self, *largs):
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
            self.cb1 = CEFBrowser(url="http://jegger.ch/datapool/app/test_popup.html", pos=(0,0), size=(wid-1, hei-100))
            self.cb1.popup_policy = popup_policy_handler
            self.cb1.popup_handler = popup_handler
            self.cb1.close_handler = close_handler
            self.cb1.bind(url=url_handler)
            self.cb1.bind(title=title_handler)
            self.cb2 = CEFBrowser(url="https://yoga-und-entspannung.ch/", pos=(wid+1,0), size=(wid-1, hei-100))
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

    CEFBrowserApp().run()

    cefpython.Shutdown()

