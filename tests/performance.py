#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
"""

if False:
    from kivy.app import App
    from kivy.garden.cefpython import CEFBrowser

    if __name__ == '__main__':
        class PerformanceTesterApp(App):
            def build(self):
                CEFBrowser.update_command_line_switches({
                    "enable-media-stream": "",
                })
                return CEFBrowser(url="http://youtube.com")
                # http://cdn.peerjs.com/demo/videochat/
                # http://www.craftymind.com/factory/html5video/CanvasVideo.html
                # http://peacekeeper.futuremark.com/

        PerformanceTesterApp().run()

if True:
    from kivy.app import App
    from kivy.clock import Clock
    from kivy.graphics import Color, Rectangle
    from kivy.graphics.texture import Texture
    from kivy.uix.widget import Widget

    import time
    import random

    if __name__ == '__main__':
        global w, r
        w = Widget()
        with w.canvas:
            Color(1, 1, 1)
            r = Rectangle(pos=w.pos, size=w.size)

        class PerformanceTesterApp(App):
            def build(self):
                return w

        w.mv = None

        texture_size_hint = 1

        def update(*largs):
            global r, w
            print("BEF", w, r.texture, r.texture.width, r.texture.height)
            half = int(
                w.size[0] * w.size[1] * texture_size_hint *
                texture_size_hint / 2,
            )
            if not w.mv:
                r.texture = Texture.create(
                    size=(
                        w.size[0]*texture_size_hint,
                        w.size[1]*texture_size_hint,
                    ),
                    colorfmt="rgba", bufferfmt="ubyte")
                w.ba = bytearray([255, 0, 0] * half + [0, 255, 0] * half)
                w.mv = memoryview(w.ba)
            else:
                for i in range(
                    random.randint(0, half*3),
                    random.randint(half * 3, 2 * half * 3),
                ):
                    w.ba[i] = 255
            beg = time.time()
            r.texture.blit_buffer(w.mv)
            print(time.time() - beg)
            r.size = w.size
            print("AFT", w, r.texture, r.texture.width, r.texture.height)

        Clock.schedule_interval(update, 2)

        PerformanceTesterApp().run()
