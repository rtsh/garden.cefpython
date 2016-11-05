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
e.g. downloads which aren't implemented or causing proplems.
Tested on Ubuntu 14.04.1 LTS 64bit with the following debian packages
installed:
- `libnss3-1d`
- `libnspr4-0d`

If it does not work on Windows, it is most probably because not all the
needed DLLs are copied correctly from the downloaded ZIP file. You would then
need to edit `lib/cefpython_sources.json`.


How to develop with virtualenv
------------------------------

1. Create a virtualenv: `virtualenv venv`
2. Install kivy into virtualenv (consult kivy docs for this)
3. Install other dependencies into virtualenv: `venv/bin/pip install -r requirements.txt`
4. Symlink cefbrowser into graden directory: `ln -s path/to/gardne.cefpython ~/.kivy/garden/garden.cefpython`
5. Now you should be able to launch one of the examples: `venv/bin/python examples/minimal.py`


How to develop with virtualenv and prebuilt packages from Rentouch (Py2.7 & Linux)
----------------------------------------------------------------------------------
1. Create a virtual: `virtualenv venv`
2. Update Pip: `venv/bin/pip install -U pip`
3. Install Kivy into venv: `venv/bin/pip install Kivy==1.9.2-dev0xinput4 --index-url https://wheels.rentouch.ch`
   If you get an cert-mismatch error: use: `venv/bin/pip install Kivy==1.9.2-dev0xinput4 --index-url https://wheels.rentouch.ch --trusted-host wheels.rentouch.ch`
4. Install other required libraries (as Cefpython) by: `venv/bin/pip install -r requirements.txt --index-url https://wheels.rentouch.ch --trusted-host wheels.rentouch.ch`
5. Create garden folder if not existing: `mkdir ~/.kivy/garden`
6. Symlink garden.cefpython into graden directory: `ln -s path/to/this/garden.cefpython ~/.kivy/garden/garden.cefpython`
7. Now you should be able to launch one of the examples: `venv/bin/python examples/minimal.py`


How to develop with virtualenv and prebuilt packages from Rentouch (Py3 & Linux)
----------------------------------------------------------------------------------
Basically you have to follow the steps for 2.7 above:

1. `virtualenv -p python3 3venv`
2. `3venv/bin/pip install Kivy==1.9.2-dev0xinput4 --index-url https://wheels.rentouch.ch --trusted-host wheels.rentouch.ch`
3. `3venv/bin/pip install cefpython3`
4. `ln -s path/to/this/garden.cefpython ~/.kivy/garden/garden.cefpython`


Known Issues
------------

- Documentation is poor
- API (Methods of CEFBrowser) *will* still be subject to change
- Keyboards sometimes don't vanish, when another element is focused, system
    keyboard input is sometimes redirected to multiple focused elements, etc.


Contribute
----------

- Test on all operating systems and file bug reports
