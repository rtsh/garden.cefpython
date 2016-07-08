#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""'
This library provides functions to automatically download the precompiled
.so/.dll files from the cefpython repository if not already found in
PYTHONPATH.
It then imports the cefpython module.
"""

__all__ = ('cefpython', )

import atexit
import ctypes
import json
import os
import signal
import sys
import multiprocessing

import kivy
kivy.require("1.8.0")
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger


PLATFORM = kivy.platform
PYVERSION = sys.version_info[0]
BITS = "64" if sys.maxsize > 2**32 else "32"
PARDIR = os.path.realpath(os.path.dirname(__file__))
CURDIR = os.path.join(PARDIR, "cefpython")
LIB_ID = "%s%s.py%i"%(PLATFORM, BITS, PYVERSION)
CEF_DIR = os.path.join(CURDIR, LIB_ID)
SUBPROCESS = "subprocess"
fp = open(os.path.join(PARDIR, "cefpython_sources.json"), "r")
SOURCES = json.load(fp)
fp.close()
Logger.debug("CEFLoader: PLATFORM: %s", PLATFORM)
Logger.debug("CEFLoader: PYVERSION: %s", PYVERSION)
Logger.debug("CEFLoader: BITS: %s", BITS)
Logger.debug("CEFLoader: PARDIR: %s", PARDIR)
Logger.debug("CEFLoader: CURDIR: %s", CURDIR)
Logger.debug("CEFLoader: LIB_ID: %s", LIB_ID)
Logger.debug("CEFLoader: CEF_DIR: %s", CEF_DIR)
Logger.debug("CEFLoader: SUBPROCESS: %s", SUBPROCESS)
Logger.info("CEFLoader: LIB_ID: %s", LIB_ID)


#
# Try import from package (PYTHONPATH)
try:
    from cefpython3 import cefpython
    Logger.info("CEFLoader: cefpython3 imported from package")
except ImportError:
    if PLATFORM == 'linux':
        # correctly locate libcef.so (we need to extend
        # LD_LIBRARY_PATH for subprocess executable)
        libcef = os.path.join(CEF_DIR, "libcef.so")
        LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', None)
        if not LD_LIBRARY_PATH:
            LD_LIBRARY_PATH = CEF_DIR
        else:
            LD_LIBRARY_PATH += os.pathsep + CEF_DIR
        os.putenv('LD_LIBRARY_PATH', LD_LIBRARY_PATH)
    elif PLATFORM == 'win':
        # Add the DLL and export the PATH for windows
        SUBPROCESS += ".exe"
        libcef = os.path.join(CEF_DIR, "libcef.dll")
        PATH = os.environ.get('PATH', None)
        if not PATH:
            PATH = CEF_DIR
        else:
            PATH += os.pathsep + CEF_DIR
        os.putenv('PATH', PATH)
    else:
        Logger.critical("CEFLoader: Unsupported platform: %s", PLATFORM)
        raise Exception("Unsupported platform")
    sys.path += [CEF_DIR]

    # Load precompiled cefpython from source
    if not os.path.exists(libcef) and LIB_ID in SOURCES:
        s = SOURCES[LIB_ID]
        Logger.debug("CEFLoader: SOURCE: %s", json.dumps(s, indent=4))
        Logger.info("CEFLoader: Loading precompiled cefpython for "+LIB_ID+"...")
        path = CEF_DIR+".dat"
        if os.path.exists(path):
            os.unlink(path)
        if not os.path.exists(CEF_DIR):
            os.makedirs(CEF_DIR)
        Logger.debug("CEFLoader: Downloading from "+s["url"]+" ...")

        from kivy.app import App
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.popup import Popup
        from kivy.uix.progressbar import ProgressBar

        content = BoxLayout(orientation='vertical')
        prgr = ProgressBar(max=100)
        prgr.value = 0
        content.add_widget(prgr)
        lab = Label(text="Downloading precompiled CEFPython...")
        content.add_widget(lab)

        popup = Popup(title="Chromium Embedded Framework Installer", content=content, size_hint=(0.75, None), height=200, auto_dismiss=False)
        # content.bind(on_press=popup.dismiss) # shouldn't be, right?

        def download(s, path, progress, label_queue):
            import urllib2
            fp = open(path, "w+")
            fh = urllib2.urlopen(s["url"])
            buf = True
            cur = 0
            tot = int(fh.info()["Content-Length"])
            stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
            lastpercent = 0
            while buf:
                buf = fh.read(8192)
                cur += len(buf)
                percent = cur*100./tot
                stdout.write("Downloading: %3i%%\r"%(percent,))
                stdout.flush()
                progress.value = percent*0.8
                if int(percent)!=lastpercent:
                    label_queue.put("Downloading precompiled CEFPython... (%i%%)"%(percent,), False)
                    lastpercent = int(percent)
                fp.write(buf)
            fh.close()
            fp.close()
            Logger.info("CEFLoader: Loaded precompiled cefpython for "+LIB_ID+" successfully")
            if "type" in s:
                if s["type"]=="zip":
                    Logger.info("CEFLoader: Unzipping precompiled cefpython for "+LIB_ID+"...")
                    label_queue.put("Unzipping precompiled CEFPython...", False)
                    progress.value = percent*0.8
                    import shutil
                    import zipfile
                    z = zipfile.ZipFile(path)
                    z.extractall(CURDIR)
                    cnt = len(s["zip_files"])
                    i = 0
                    for f in s["zip_files"]:
                        label_queue.put("Unzipping precompiled CEFPython... (%i of %i)"%(i, cnt), False)
                        progress.value = 80+float(i)*20./cnt
                        src = os.path.join(CURDIR, s["zip_files"][f].replace("/", os.sep))
                        dest = os.path.join(CEF_DIR, f)
                        Logger.debug("CEFLoader: Copying "+src+" => "+dest+" ...")
                        if os.path.isfile(src):
                            shutil.copy(src, dest)
                        elif os.path.isdir(src):
                            shutil.copytree(src, dest)
                        os.chmod(dest, 0o0775)
                        i += 1
                    Logger.debug("CEFLoader: Cleaning up...")
                    label_queue.put("Cleaning up...", False)
                    n = z.namelist()[0]
                    ziproot = n[0:n.find(os.sep)]
                    shutil.rmtree(os.path.join(CURDIR, ziproot))
                    Logger.info("CEFLoader: Unzipped precompiled cefpython for "+LIB_ID+" successfully")
                    label_queue.put("Finished.", False)
                    progress.value = 100.
                else:
                    Logger.warning("CEFLoader: Invalid source entry for "+LIB_ID+": 'type' not known: "+s["type"]+"")
            else:
                Logger.warning("CEFLoader: Incomplete source entry for "+LIB_ID+": 'type' key not present")
            os.unlink(path)

        progress = multiprocessing.Value('d', 0.0)
        label_queue = multiprocessing.Queue()
        download_proc = multiprocessing.Process(target=download, args=(s, path, progress, label_queue))

        class CefLoaderApp(App):
            def on_start(self):
                popup.open()
        cef_loader_app = CefLoaderApp()

        download_proc.start()
        def test_download(*largs):
            try:
                while True:
                    lab.text = label_queue.get(False)
            except:
                pass
            prgr.value = progress.value
            if download_proc.is_alive():
                Clock.schedule_once(test_download, 0.05)
            else:
                popup.dismiss(force=True)
                cef_loader_app.stop()
        Clock.schedule_once(test_download, 0.05)
        cef_loader_app.run()

    # Import local module
    try:
        ctypes.CDLL(libcef, ctypes.RTLD_GLOBAL)
        if 0x02070000 <= sys.hexversion < 0x03000000:
            import cefpython_py27 as cefpython
            Logger.info("CEFLoader: cefpython imported from %s"%(libcef, ))
        else:
            Logger.critical("CEFLoader: Unsupported python version: %s"%(sys.version, ))
            raise Exception("Unsupported python version: %s"%(sys.version, ))
    except:
        Logger.critical("CEFLoader: Failed to import cefpython")
        raise Exception("Failed to import cefpython")

cefpython_loop_event = None

def cefpython_initialize(CEFBrowser):
    global cefpython_loop_event
    if cefpython_loop_event:
        Logger.warning("CEFLoader: Attempt to initialize CEFPython another time")
        return
    try:
        md = cefpython.GetModuleDirectory()
    except Exception as e:
        raise Exception("CEFLoader: Could not define module-directory: %s" % e)
    Logger.debug("CEFLoader: Module Directory: %s", md)

    def cef_loop(*largs):
        try:
            cefpython.MessageLoopWork()
        except Exception as e:
            print("EXCEPTION IN CEF LOOP", e)
    cefpython_loop_event = Clock.schedule_interval(cef_loop, 0.01)

    default_settings = {
        "debug": False,
        "log_severity": cefpython.LOGSEVERITY_INFO,
        "release_dcheck_enabled": True,  # Enable only when debugging.
        "locales_dir_path": os.path.join(md, "locales"),
        "resources_dir_path": md,
        "browser_subprocess_path": os.path.join(md, SUBPROCESS),
        "unique_request_context_per_browser": True,
        "windowless_rendering_enabled": True,
        "context_menu": {"enabled": False, },
    }
    default_settings.update(CEFBrowser._settings)
    caches_path = os.path.join(md, "caches")
    cookies_path = os.path.join(md, "cookies")
    logs_path = os.path.join(md, "logs")
    if CEFBrowser._caches_path and os.path.isdir(os.path.dirname(CEFBrowser._caches_path)):
        caches_path = CEFBrowser._caches_path
    if CEFBrowser._cookies_path and os.path.isdir(os.path.dirname(CEFBrowser._cookies_path)):
        cookies_path = CEFBrowser._cookies_path
    if CEFBrowser._logs_path and os.path.isdir(os.path.dirname(CEFBrowser._logs_path)):
        logs_path = CEFBrowser._logs_path
    Logger.debug("CEFLoader: Caches path: %s", caches_path)
    Logger.debug("CEFLoader: Cookies path: %s", cookies_path)
    Logger.debug("CEFLoader: Logs path: %s", logs_path)
    if not os.path.isdir(caches_path):
        os.makedirs(caches_path, 0o0700)
    default_settings["cache_path"] = caches_path
    if not os.path.isdir(cookies_path):
        os.makedirs(cookies_path, 0o0700)
    if not os.path.isdir(logs_path):
        os.makedirs(logs_path, 0o0700)
    default_settings["log_file"] = os.path.join(logs_path, "cefpython.log")

    cefpython.WindowUtils.InstallX11ErrorHandlers()
    try:
        cefpython.Initialize(default_settings, CEFBrowser._command_line_switches)
    except Exception as err:
        del default_settings["debug"]
        cefpython.g_debug = True
        cefpython.g_debugFile = "debug.log"
        try:
            cefpython.Initialize(default_settings, CEFBrowser._command_line_switches)
        except Exception as err:
            raise Exception("CEFLoader: Failed to initialize cefpython %s", err)

    try:
        cookie_manager = cefpython.CookieManager.GetGlobalManager()
        cookie_manager.SetStoragePath(cookies_path, True)
        CEFBrowser._cookie_manager = cookie_manager
    except Exception as e:
        Logger.warning("CEFLoader: Failed to set up cookie manager: %s" % e)

    def cefpython_shutdown(*largs):
        print "CEFPYTHON SHUTDOWN", largs, App.get_running_app()
        cefpython.Shutdown()
        App.get_running_app().stop()
    def cefpython_exit(*largs):
        cefpython_shutdown()
        sys.exit()
    atexit.register(cefpython_shutdown)
    signal.signal(signal.SIGINT, cefpython_exit)
