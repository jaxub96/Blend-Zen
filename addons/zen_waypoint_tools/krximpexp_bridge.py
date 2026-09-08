"""
Bridge to KrxImpExp's plain-callable import functions.

The installed addon's module name is a hash-suffixed string
(e.g. "krximpexp-c20f0350a528e53f9bddc158f3cc18b6bfec61c1") that changes
whenever the addon is reinstalled/updated, so it can't be imported by a
fixed name. This resolves the currently-enabled module dynamically via
addon_utils instead.

Also: this version of KrxImpExp wraps its bpy.ops entry points
(krx3dsimpgui, krxmrmimpgui, ...) in an interactive external GUI dialog,
which can't be driven headlessly. Each importer module also exposes a
plain Python function explicitly marked "for calling outside KrxImpExp
module" (Krx3dsImp(), KrxMrmImp()) - that's what we use instead.
"""

import importlib
import addon_utils


def _find_krximpexp_module_name():
    for mod in addon_utils.modules():
        if mod.__name__.startswith("krximpexp"):
            return mod.__name__
    return None


def get_krx_3ds_importer():
    """Returns Krx3dsImp(filename, scale=0.01, ...) -> loader with
    .imported_objects, or raises RuntimeError if krximpexp isn't
    installed/enabled."""
    module_name = _find_krximpexp_module_name()
    if module_name is None:
        raise RuntimeError("krximpexp addon is not installed or enabled")
    mod = importlib.import_module(f"{module_name}.Krx3dsImp")
    return mod.Krx3dsImp


def get_krx_mrm_importer():
    """Returns KrxMrmImp(filename, scale=0.01, ...) - creates objects
    directly (no return value), so callers should diff bpy.data.objects
    before/after to find what was created."""
    module_name = _find_krximpexp_module_name()
    if module_name is None:
        raise RuntimeError("krximpexp addon is not installed or enabled")
    mod = importlib.import_module(f"{module_name}.KrxMrmImp")
    return mod.KrxMrmImp


def get_krx_3ds_exporter():
    """Returns Krx3dsExp(filename, selected_objects_param=None,
    use_local_cs=True, scale=100, matlib_file_path=None, ...)."""
    module_name = _find_krximpexp_module_name()
    if module_name is None:
        raise RuntimeError("krximpexp addon is not installed or enabled")
    mod = importlib.import_module(f"{module_name}.Krx3dsExp")
    return mod.Krx3dsExp
