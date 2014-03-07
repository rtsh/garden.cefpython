'''
Cef Keyboard Manager.
Cef Keyboard management is complex, so we outsourced it to this file for
better readability.
'''
from lib.cefpython import *

class CefKeyboardManagerSingleton():
    # Kivy does not provide modifiers in on_key_up, but these
    # must be sent to CEF as well.
    is_shift1 = False
    is_shift2 = False
    is_ctrl1 = False
    is_ctrl2 = False
    is_alt1 = False
    is_alt2 = False

    def __init__ (self, *largs, **dargs):
        pass
    
    def reset_all_modifiers(self):
        self.is_shift1 = False
        self.is_shift2 = False
        self.is_ctrl1 = False
        self.is_ctrl2 = False
        self.is_alt1 = False
        self.is_alt2 = False
    
    def kivy_on_key_down(self, browser, keyboard, keycode, text, modifiers):
        # Notes:
        # - right alt modifier is not sent by Kivy through modifiers param.
        # print("on_key_down(): keycode = %s, text = %s, modifiers = %s" % (
        #         keycode, text, modifiers))
        if keycode[0] == 27:
            # On escape release the keyboard, see the injected
            # javascript in OnLoadStart().
            browser.GetFocusedFrame().ExecuteJavascript("__kivy__on_escape()")
            return
        cefModifiers = cefpython.EVENTFLAG_NONE
        if "shift" in modifiers:
            cefModifiers |= cefpython.EVENTFLAG_SHIFT_DOWN
        if "ctrl" in modifiers:
            cefModifiers |= cefpython.EVENTFLAG_CONTROL_DOWN
        if "alt" in modifiers:
            cefModifiers |= cefpython.EVENTFLAG_ALT_DOWN
        if "capslock" in modifiers:
            cefModifiers |= cefpython.EVENTFLAG_CAPS_LOCK_ON
        # print("on_key_down(): cefModifiers = %s" % cefModifiers)
        cef_keycode = self.translate_to_cef_keycode(keycode[0])
        keyEvent = {
                "type": cefpython.KEYEVENT_RAWKEYDOWN,
                "native_key_code": cef_keycode,
                "modifiers": cefModifiers
                }
        # print("keydown keyEvent: %s" % keyEvent)
        browser.SendKeyEvent(keyEvent)
        if keycode[0] == 304:
            self.is_shift1 = True
        elif keycode[0] == 303:
            self.is_shift2 = True
        elif keycode[0] == 306:
            self.is_ctrl1 = True
        elif keycode[0] == 305:
            self.is_ctrl2 = True
        elif keycode[0] == 308:
            self.is_alt1 = True
        elif keycode[0] == 313:
            self.is_alt2 = True

    def kivy_on_key_up(self, browser, keyboard, keycode):
       # print("on_key_up(): keycode = %s" % (keycode,))
        cefModifiers = cefpython.EVENTFLAG_NONE
        if self.is_shift1 or self.is_shift2:
            cefModifiers |= cefpython.EVENTFLAG_SHIFT_DOWN
        if self.is_ctrl1 or self.is_ctrl2:
            cefModifiers |= cefpython.EVENTFLAG_CONTROL_DOWN
        if self.is_alt1:
            cefModifiers |= cefpython.EVENTFLAG_ALT_DOWN
        # Capslock todo.
        cef_keycode = self.translate_to_cef_keycode(keycode[0])
        keyEvent = {
                "type": cefpython.KEYEVENT_KEYUP,
                "native_key_code": cef_keycode,
                "modifiers": cefModifiers
                }
        # print("keyup keyEvent: %s" % keyEvent)
        browser.SendKeyEvent(keyEvent)
        keyEvent = {
                "type": cefpython.KEYEVENT_CHAR,
                "native_key_code": cef_keycode,
                "modifiers": cefModifiers
                }
        # print("char keyEvent: %s" % keyEvent)
        browser.SendKeyEvent(keyEvent)
        if keycode[0] == 304:
            self.is_shift1 = False
        elif keycode[0] == 303:
            self.is_shift2 = False
        elif keycode[0] == 306:
            self.is_ctrl1 = False
        elif keycode[0] == 305:
            self.is_ctrl2 = False
        elif keycode[0] == 308:
            self.is_alt1 = False
        elif keycode[0] == 313:
            self.is_alt2 = False
    
    def translate_to_cef_keycode(self, keycode):
        # TODO: this works on Linux, but on Windows the key
        #       mappings will probably be different.
        # TODO: what if the Kivy keyboard layout is changed
        #       from qwerty to azerty? (F1 > options..)
        cef_keycode = keycode
        if self.is_alt2:
            # The key mappings here for right alt were tested
            # with the utf-8 charset on a webpage. If the charset
            # is different there is a chance they won't work correctly.
            alt2_map = {
                    # tilde
                    "96":172,
                    # 0-9 (48..57)
                    "48":125, "49":185, "50":178, "51":179, "52":188,
                    "53":189, "54":190, "55":123, "56":91, "57":93,
                    # minus
                    "45":92,
                    # a-z (97..122)
                    "97":433, "98":2771, "99":486, "100":240, "101":490,
                    "102":496, "103":959, "104":689, "105":2301, "106":65121,
                    "107":930, "108":435, "109":181, "110":497, "111":243,
                    "112":254, "113":64, "114":182, "115":438, "116":956,
                    "117":2302, "118":2770, "119":435, "120":444, "121":2299,
                    "122":447,
                    }
            if str(keycode) in alt2_map:
                cef_keycode = alt2_map[str(keycode)]
            else:
                print("Kivy to CEF key mapping not found (right alt), " \
                        "key code = %s" % keycode)
            shift_alt2_map = {
                    # tilde
                    "96":172,
                    # 0-9 (48..57)
                    "48":176, "49":161, "50":2755, "51":163, "52":36,
                    "53":2756, "54":2757, "55":2758, "56":2761, "57":177,
                    # minus
                    "45":191,
                    # A-Z (97..122)
                    "97":417, "98":2769, "99":454, "100":208, "101":458,
                    "102":170, "103":957, "104":673, "105":697, "106":65122,
                    "107":38, "108":419, "109":186, "110":465, "111":211,
                    "112":222, "113":2009, "114":174, "115":422, "116":940,
                    "117":2300, "118":2768, "119":419, "120":428, "121":165,
                    "122":431,
                    # special: <>?  :"  {}
                    "44":215, "46":247, "47":65110,
                    "59":65113, "39":65114,
                    "91":65112, "93":65108,
                    }
            if self.is_shift1 or self.is_shift2:
                if str(keycode) in shift_alt2_map:
                    cef_keycode = shift_alt2_map[str(keycode)]
                else:
                    print("Kivy to CEF key mapping not found " \
                            "(shift + right alt), key code = %s" % keycode)
        elif self.is_shift1 or self.is_shift2:
            shift_map = {
                    # tilde
                    "96":126,
                    # 0-9 (48..57)
                    "48":41, "49":33, "50":64, "51":35, "52":36, "53":37,
                    "54":94, "55":38, "56":42, "57":40,
                    # minus, plus
                    "45":95, "61":43,
                    # a-z (97..122)
                    "97":65, "98":66, "99":67, "100":68, "101":69, "102":70,
                    "103":71, "104":72, "105":73, "106":74, "107":75, "108":76,
                    "109":77, "110":78, "111":79, "112":80, "113":81, "114":82,
                    "115":83, "116":84, "117":85, "118":86, "119":87, "120":88,
                    "121":89, "122":90,
                    # special: <>?  :"  {}
                    "44":60, "46":62, "47":63,
                    "59":58, "39":34,
                    "91":123, "93":125,
            }
            if str(keycode) in shift_map:
                cef_keycode = shift_map[str(keycode)]
        # Other keys:
        other_keys_map = {
            # Escape
            "27":65307,
            # F1-F12
            "282":65470, "283":65471, "284":65472, "285":65473,
            "286":65474, "287":65475, "288":65476, "289":65477,
            "290":65478, "291":65479, "292":65480, "293":65481,
            # Tab
            "9":65289,
            # Left Shift, Right Shift
            "304":65505, "303":65506,
            # Left Ctrl, Right Ctrl
            "306":65507, "305": 65508,
            # Left Alt, Right Alt
            "308":65513, "313":65027,
            # Backspace
            "8":65288,
            # Enter
            "13":65293,
            # PrScr, ScrLck, Pause
            "316":65377, "302":65300, "19":65299,
            # Insert, Delete,
            # Home, End,
            # Pgup, Pgdn
            "277":65379, "127":65535,
            "278":65360, "279":65367,
            "280":65365, "281":65366,
            # Arrows (left, up, right, down)
            "276":65361, "273":65362, "275":65363, "274":65364,
        }
        if str(keycode) in other_keys_map:
            cef_keycode = other_keys_map[str(keycode)]
        return cef_keycode


CefKeyboardManager = CefKeyboardManagerSingleton()
