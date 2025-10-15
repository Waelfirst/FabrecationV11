# Install compatibility for odoo.tools.facade (removed in Odoo 17)
from .odoo_tools_facade_compat import install_facade_compatibility
install_facade_compatibility()

from . import models
from .hooks import pre_init_hook, post_init_hook

