CEF browser widget
==================

This is a widget that embeds [cefpython](https://code.google.com/p/cefpython)
into a Kivy widget.

It has been tested only on Linux 64bit so far.


Example
-------

    from kivy.app import App
    from kivy.garden.cefpython import CEFBrowser

    class SimpleBrowserApp(App):
        def build(self):
            return CEFBrowser(url="http://kivy.org")
    SimpleBrowserApp().run()


Status
------

This project shouldn't be considered stable. There are many things, as 
e.g. downloads or keyboard input which aren't implemented or causing proplems.
Tested on Ubuntu 14.04.1 LTS 64bit with the follwoing debian packages
installed:
- `libnss3-1d`
- `libnspr4-0d`

If it does not work on Windows, it is most probably because not all the
needed DLLs are copied correctly from the downloaded ZIP file. You would then
need to edit `lib/cefpython_sources.json`.


Known Issues
------------

- Documentation is poor
- API (Methods of CEFBrowser) *will* still be subject to change
- Keyboards sometimes don't vanish, when another element is focused, system
    keyboard input is sometimes redirected to multiple focused elements, etc.


Contribute
----------

- Test on all operating systems and file bug reports
