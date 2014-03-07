CEF widget
----------

This is a widget that embed [cefpython](https://code.google.com/p/cefpython)
into a Kivy widget.
Works currently on Linux and Windows 64bit with python 2.7.

This project shouldn't be considered stable. There are major things 
(e.g. popups) which aren't implemented or causing proplems.
Tested on Ubuntu 12.04 64bit with the follwoing debian packages installed:
`libnss3-1d libnspr4-0d`
If it does not work on Windows, it is most probably, because not all the
needed DLLs are copied correctly from the downloaded ZIP file. You would then
need to edit `lib/cefpython_sources.json`.


Example
-------

    from kivy.garden.cefpython import CefBrowser, cefpython
    from kivy.app import App

    class CefBrowserApp(App):
        def build(self):
            return CefBrowser(start_url='http://kivy.org')

    CefBrowserApp().run()
    
    cefpython.Shutdown()

