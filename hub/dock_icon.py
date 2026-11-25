"""The icon of Azimuth.app on macOS follows the theme of the program.

While the program runs, the Dock shows the window icon (azimuth.app.app_icon, light or dark tile in
the colours of the side panel). After the program closes, the Dock and the Finder show the icon of the
bundle, which was always the light Azimuth.icns: a white tile right after quitting a dark program. When
the theme changes, sync(dark) gives Azimuth.app the same tile as a custom icon (NSWorkspace
setIcon:forFile:options:, through the Objective-C runtime with ctypes: no extra package). The variant
written last is kept in QSettings, so the bundle is touched only when the theme really changes.
Elsewhere (Windows, Linux, offscreen tests, no bundle) it does nothing.
"""

import ctypes
import ctypes.util
import os
import sys

from azimuth.paths import ROOT

BUNDLE = ROOT / 'Azimuth.app'
KEY = 'dock_icon'


def icon_file(dark):
    return ROOT / 'assets' / 'app-icon' / ('dark' if dark else '') / 'azimuth-1024.png'


def available():
    if sys.platform != 'darwin' or not BUNDLE.is_dir():
        return False
    if os.environ.get('QT_QPA_PLATFORM', '').startswith('offscreen') or os.environ.get('PYTEST_CURRENT_TEST'):
        return False
    return True


def _set_icon(image, target):
    """NSWorkspace.sharedWorkspace setIcon:image forFile:target options:0 -> bool."""
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
    ctypes.cdll.LoadLibrary(ctypes.util.find_library('AppKit'))
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]

    def send(restype, receiver, selector, *args):
        types = [ctypes.c_void_p, ctypes.c_void_p] + [kind for kind, _ in args]
        function = ctypes.cast(objc.objc_msgSend, ctypes.CFUNCTYPE(restype, *types))
        return function(receiver, objc.sel_registerName(selector.encode()), *[value for _, value in args])

    def string(text):
        return send(ctypes.c_void_p, objc.objc_getClass(b'NSString'), 'stringWithUTF8String:', (ctypes.c_char_p, text.encode('utf-8')))

    picture = send(ctypes.c_void_p, objc.objc_getClass(b'NSImage'), 'alloc')
    picture = send(ctypes.c_void_p, picture, 'initWithContentsOfFile:', (ctypes.c_void_p, string(str(image))))
    if not picture:
        return False
    try:
        workspace = send(ctypes.c_void_p, objc.objc_getClass(b'NSWorkspace'), 'sharedWorkspace')
        return bool(
            send(
                ctypes.c_bool,
                workspace,
                'setIcon:forFile:options:',
                (ctypes.c_void_p, picture),
                (ctypes.c_void_p, string(str(target))),
                (ctypes.c_ulong, 0),
            )
        )
    finally:
        send(None, picture, 'release')


def sync(dark, preferences=None):
    """Give Azimuth.app the light or dark tile; True when the bundle icon was written now."""
    if not available():
        return False
    variant = 'dark' if dark else 'light'
    if preferences is not None and preferences.value(KEY, '') == variant:
        return False
    try:
        done = _set_icon(icon_file(dark), BUNDLE)
    except Exception as error:  # never let the icon stop the program
        print(f'Azimuth: the bundle icon was not changed: {error}')
        return False
    if done and preferences is not None:
        preferences.setValue(KEY, variant)
    return done
