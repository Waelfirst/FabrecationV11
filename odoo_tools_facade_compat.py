"""
Compatibility module for odoo.tools.facade

The odoo.tools.facade module existed in older Odoo versions (before v17) but was removed
in Odoo 17 as part of the framework modernization. However, some third-party modules or
legacy code may still attempt to import from it.

This compatibility module provides basic implementations of Proxy, ProxyAttr, and ProxyFunc
classes to prevent ModuleNotFoundError when such imports are encountered.

Usage:
    This module is automatically installed when the Steel Structure Project module is loaded.
    The install_facade_compatibility() function registers the facade module in sys.modules,
    allowing any code that imports from odoo.tools.facade to work without errors.

Note:
    These are minimal implementations designed for compatibility only. If your code
    heavily relies on the original facade functionality, you may need to extend these
    classes with additional features.
"""

import sys


class Proxy:
    """
    Basic Proxy class for compatibility.
    In older Odoo versions, this was used for lazy loading and proxying objects.
    """
    def __init__(self, target=None):
        self._target = target
    
    def __getattr__(self, name):
        if self._target is None:
            raise AttributeError(f"Proxy has no target set")
        return getattr(self._target, name)
    
    def __setattr__(self, name, value):
        if name == '_target':
            object.__setattr__(self, name, value)
        else:
            if self._target is None:
                raise AttributeError(f"Proxy has no target set")
            setattr(self._target, name, value)


class ProxyAttr:
    """
    Proxy for attributes.
    Provides lazy attribute access.
    """
    def __init__(self, obj, attr):
        self._obj = obj
        self._attr = attr
    
    def __call__(self, *args, **kwargs):
        target = getattr(self._obj, self._attr)
        if callable(target):
            return target(*args, **kwargs)
        return target
    
    def __getattr__(self, name):
        target = getattr(self._obj, self._attr)
        return getattr(target, name)


class ProxyFunc:
    """
    Proxy for functions.
    Provides lazy function call wrapping.
    """
    def __init__(self, func):
        self._func = func
    
    def __call__(self, *args, **kwargs):
        return self._func(*args, **kwargs)
    
    def __getattr__(self, name):
        return getattr(self._func, name)


def install_facade_compatibility():
    """
    Install the facade compatibility module into sys.modules.
    This allows code that imports from odoo.tools.facade to work.
    """
    # Create a fake module object
    import types
    facade_module = types.ModuleType('odoo.tools.facade')
    facade_module.__file__ = __file__
    facade_module.__package__ = 'odoo.tools'
    
    # Add the classes to the module
    facade_module.Proxy = Proxy
    facade_module.ProxyAttr = ProxyAttr
    facade_module.ProxyFunc = ProxyFunc
    
    # Register it in sys.modules
    sys.modules['odoo.tools.facade'] = facade_module
    
    return facade_module
