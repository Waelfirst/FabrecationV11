# Install compatibility for odoo.tools.facade (removed in Odoo 17)
# The odoo.tools.facade module was deprecated and removed in Odoo 17.
# This compatibility shim provides the missing Proxy, ProxyAttr, and ProxyFunc classes
# to prevent ModuleNotFoundError when other modules or dependencies try to import them.
# This must be installed before any other imports to ensure availability.
from .odoo_tools_facade_compat import install_facade_compatibility
install_facade_compatibility()

from . import models
from .hooks import pre_init_hook, post_init_hook

