"""
Compatibility module for odoo.tools.facade

The odoo.tools.facade module was removed in Odoo 17.
This module provides basic compatibility shims for code that still references it.
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
