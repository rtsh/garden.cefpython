'''
This library providers functions to automatically download the precompiled
.so/.dll files from the cefpython repository.
It then imports the cefpython module.
'''

__all__ = ('cefpython', 'test_url')

from kivy.clock import Clock
from os.path import dirname, join, exists, realpath
import ctypes
import json
import os
import sys

PLATFORM = "linux"
try: # New API
    from kivy import platform
    PLATFORM = platform
except: # Deprecated API
    from kivy.utils import platform
    PLATFORM = platform()
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

if PLATFORM == 'linux':
    # correctly locate libcef.so (we need to extend
    # LD_LIBRARY_PATH for subprocess executable)
    libcef = join(CEF_DIR, 'libcef.so')
    LD_LIBRARY_PATH = os.environ.get('LD_LIBRARY_PATH', None)
    if not LD_LIBRARY_PATH:
        LD_LIBRARY_PATH = CEF_DIR
    else:
        LD_LIBRARY_PATH += os.pathsep + CEF_DIR
    os.putenv('LD_LIBRARY_PATH', LD_LIBRARY_PATH)
elif PLATFORM == 'win':
    # Add the DLL and export the PATH for windows
    SUBPROCESS += ".exe"
    libcef = join(CEF_DIR, 'libcef.dll')
    PATH = os.environ.get('PATH', None)
    if not PATH:
        PATH = CEF_DIR
    else:
        PATH += os.pathsep + CEF_DIR
    os.putenv('PATH', PATH)
else:
    raise Exception("Unsupported/untested platform.")
sys.path += [CEF_DIR]

# Load precompiled cefpython from source
if not exists(libcef) and LIB_ID in SOURCES:
    s = SOURCES[LIB_ID]
    print "Load precompiled cefpython (for "+LIB_ID+") from source..."
    path = CEF_DIR+".dat"
    if exists(path):
        os.unlink(path)
    if not exists(CEF_DIR):
        os.mkdir(CEF_DIR)
    import urllib2
    fp = open(path, "w+")
    fh = urllib2.urlopen(s["url"])
    buf = True
    while buf:
        buf = fh.read(4096)
        fp.write(buf)
    fh.close()
    fp.close()
    if "type" in s:
        if s["type"]=="zip":
            print "Unzipping..."
            import shutil
            import zipfile
            z = zipfile.ZipFile(path)
            z.extractall(CURDIR)
            for f in s["zip_files"]:
                src = join(CURDIR, s["zip_files"][f].replace("/", os.sep))
                dest = join(CEF_DIR, f)
                print "Copy "+f+"..."
                if os.path.isfile(src):
                    shutil.copy(src, dest)
                elif os.path.isdir(src):
                    shutil.copytree(src, dest)
                os.chmod(dest, 0775)
            print "Clean up..."
            n = z.namelist()[0]
            ziproot = n[0:n.find(os.sep)]
            shutil.rmtree(join(CURDIR, ziproot))
        else:
            print "Invalid source entry for "+LIB_ID+": 'type' not known: "+s["type"]+"."
    else:
        print "Uncomplete source entry for "+LIB_ID+": 'type' key not present."
    os.unlink(path)

if exists(libcef):
    # Import local module
    ctypes.CDLL(libcef, ctypes.RTLD_GLOBAL)
    if 0x02070000 <= sys.hexversion < 0x03000000:
        import cefpython_py27 as cefpython
        print "cefpython imported from %s"%(libcef, )
    else:
        raise Exception("Unsupported python version: %s" % sys.version)
else:
    # Import from package
    from cefpython3 import cefpython
    print "cefpython imported from package"

md = ""
try:
    md = cefpython.GetModuleDirectory()
    def cef_loop(*largs):
        cefpython.MessageLoopWork()
    Clock.schedule_interval(cef_loop, 0)
except:
    raise Exception("cefpython was not imported.")
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
    cefpython.Initialize(settings)
test_url = "file://"+join(dirname(PARDIR), "test.html")
