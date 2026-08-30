from __future__ import annotations

import ctypes
import logging
import sys


logger = logging.getLogger(__name__)
_background_only_requested = False


def make_process_background_only() -> None:
    """Keep a macOS Python daemon out of the Dock before native runtimes initialize."""
    global _background_only_requested
    _background_only_requested = True
    _apply_background_only_policy()


def reassert_process_background_only() -> None:
    """Restore daemon policy after a native runtime temporarily promotes the process."""
    if _background_only_requested:
        _apply_background_only_policy()


def _apply_background_only_policy() -> None:
    if sys.platform != "darwin":
        return
    try:
        objc = ctypes.cdll.LoadLibrary("/usr/lib/libobjc.A.dylib")
        ctypes.cdll.LoadLibrary("/System/Library/Frameworks/AppKit.framework/AppKit")

        objc.objc_getClass.restype = ctypes.c_void_p
        objc.objc_getClass.argtypes = [ctypes.c_char_p]
        objc.sel_registerName.restype = ctypes.c_void_p
        objc.sel_registerName.argtypes = [ctypes.c_char_p]

        send = objc.objc_msgSend
        send.restype = ctypes.c_void_p
        send.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        application = send(
            objc.objc_getClass(b"NSApplication"),
            objc.sel_registerName(b"sharedApplication"),
        )

        set_policy = objc.objc_msgSend
        set_policy.restype = ctypes.c_bool
        set_policy.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        if not set_policy(
            application,
            objc.sel_registerName(b"setActivationPolicy:"),
            2,  # NSApplicationActivationPolicyProhibited
        ):
            logger.warning("Could not mark the Python daemon as background-only")
    except (AttributeError, OSError):
        logger.warning("Could not mark the Python daemon as background-only", exc_info=True)
