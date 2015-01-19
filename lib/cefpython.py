'''
This library providers functions to automatically download the precompiled
.so/.dll files from the cefpython repository.
It then imports the cefpython module.
'''

__all__ = ('cefpython', )

from kivy.clock import Clock
from kivy.logger import Logger
from os.path import dirname, join, exists, realpath
import ctypes
import json
import os
import sys
import multiprocessing

PLATFORM = "linux"
try: # New API
    from kivy import platform
    PLATFORM = platform
except Exception as err1:
    try: # Deprecated API
        from kivy.utils import platform
        PLATFORM = platform()
    except Exception as err2:
        Logger.warning("CEFLoader: could not get current platform: %s %s", err1, err2)
PYVERSION = sys.version_info[0]
BITS = "64" if sys.maxint > 2 ** 31 else "32"
PARDIR = realpath(dirname(__file__))
CURDIR = join(PARDIR, "cefpython")
LIB_ID = "%s%s.py%i"%(PLATFORM, BITS, PYVERSION)
CEF_DIR = join(CURDIR, LIB_ID)
SUBPROCESS = "subprocess"
fp = open(join(PARDIR, "cefpython_sources.json"), "r")
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

if PLATFORM == 'linux':
    # correctly locate libcef.so (we need to extend
    # LD_LIBRARY_PATH for subprocess executable)
    libcef = join(CEF_DIR, "libcef.so")
    LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', None)
    if not LD_LIBRARY_PATH:
        LD_LIBRARY_PATH = CEF_DIR
    else:
        LD_LIBRARY_PATH += os.pathsep + CEF_DIR
    os.putenv('LD_LIBRARY_PATH', LD_LIBRARY_PATH)
elif PLATFORM == 'win':
    # Add the DLL and export the PATH for windows
    SUBPROCESS += ".exe"
    libcef = join(CEF_DIR, "libcef.dll")
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
if not exists(libcef) and LIB_ID in SOURCES:
    s = SOURCES[LIB_ID]
    Logger.debug("CEFLoader: SOURCE: %s", json.dumps(s, indent=4))
    Logger.info("CEFLoader: Loading precompiled cefpython for "+LIB_ID+"...")
    path = CEF_DIR+".dat"
    if exists(path):
        os.unlink(path)
    if not exists(CEF_DIR):
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
    content.bind(on_press=popup.dismiss)
    
    def download(s, path, progress, label_queue):
        import urllib2
        fp = open(path, "w+")
        fh = urllib2.urlopen(s["url"])
        buf = True
        cur = 0
        tot = int(fh.info()["Content-Length"])
        stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        while buf:
            buf = fh.read(8192)
            cur += len(buf)
            percent = cur*100./tot
            stdout.write("Downloading: %3i%%\r"%(percent,))
            stdout.flush()
            progress.value = percent*0.8
            label_queue.put("Downloading precompiled CEFPython... (%i%%)"%(percent,), False)
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
                    src = join(CURDIR, s["zip_files"][f].replace("/", os.sep))
                    dest = join(CEF_DIR, f)
                    Logger.debug("CEFLoader: Copying "+src+" => "+dest+" ...")
                    if os.path.isfile(src):
                        shutil.copy(src, dest)
                    elif os.path.isdir(src):
                        shutil.copytree(src, dest)
                    os.chmod(dest, 0775)
                    i += 1
                Logger.debug("CEFLoader: Cleaning up...")
                label_queue.put("Cleaning up...", False)
                n = z.namelist()[0]
                ziproot = n[0:n.find(os.sep)]
                shutil.rmtree(join(CURDIR, ziproot))
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
        def build(self):
            return popup
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
            cef_loader_app.stop()
    Clock.schedule_once(test_download, 0.05)
    cef_loader_app.run()
    
try:
    if exists(libcef):
        # Import local module
        ctypes.CDLL(libcef, ctypes.RTLD_GLOBAL)
        if 0x02070000 <= sys.hexversion < 0x03000000:
            import cefpython_py27 as cefpython
            Logger.info("CEFLoader: cefpython imported from %s"%(libcef, ))
        else:
            Logger.critical("CEFLoader: Unsupported python version: %s"%(sys.version, ))
            raise Exception("Unsupported python version: %s"%(sys.version, ))
    else:
        # Import from package
        from cefpython3 import cefpython
        Logger.info("CEFLoader: cefpython imported from package")
except:
    Logger.critical("CEFLoader: Failed to import cefpython")
    raise Exception("Failed to import cefpython")

md = ""
try:
    md = cefpython.GetModuleDirectory()
    def cef_loop(*largs):
        try:
            cefpython.MessageLoopWork()
        except:
            print "EXCEPTION IN CEF LOOP"
    Clock.schedule_interval(cef_loop, 0)
except:
    Logger.critical("CEFLoader: cefpython was not imported")
    raise Exception("cefpython was not imported")
settings = {
    "debug": True,
    "log_severity": cefpython.LOGSEVERITY_INFO,
    "log_file": "debug.log",
    "release_dcheck_enabled": True, # Enable only when debugging.
    "locales_dir_path": join(md, "locales"),
    "resources_dir_path": md,
    "browser_subprocess_path": join(md, SUBPROCESS)
}
try:
    cefpython.Initialize(settings)
except:
    del settings["debug"]
    cefpython.g_debug = True
    cefpython.g_debugFile = "debug.log"
    try:
        cefpython.Initialize(settings)
    except:
        Logger.critical("CEFLoader: Failed to initialize cefpython")
        raise Exception("Failed to initialize cefpython")

try:
    cookie_manager = cefpython.CookieManager.GetGlobalManager()
    cookie_path = os.path.join(md, "cookies")
    cookie_manager.SetStoragePath(cookie_path, True)
except:
    Logger.warning("CEFLoader: Failed to set up cookie manager")
