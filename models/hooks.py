import logging
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)


def pre_init_hook(env):
    """
    Clean up old module data before installation/upgrade
    """
    _logger.info('Running pre_init_hook for steel_structure_project')

    cr = env.cr

    # Check if tables exist and drop them if they do
    tables_to_check = [
        'steel_project_line',
        'steel_project',
        'steel_project_dashboard',
        'steel_project_dashboard_steel_project_rel'
    ]

    for table in tables_to_check:
        cr.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = %s
            )
        """, (table,))

        if cr.fetchone()[0]:
            _logger.info(f'Table {table} exists, attempting cleanup...')
            try:
                # Try to drop constraints first
                cr.execute(f"""
                    SELECT constraint_name 
                    FROM information_schema.table_constraints 
                    WHERE table_name = '{table}' AND constraint_type = 'FOREIGN KEY'
                """)
                constraints = cr.fetchall()
                for constraint in constraints:
                    try:
                        cr.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint[0]} CASCADE")
                    except Exception as e:
                        _logger.warning(f'Could not drop constraint {constraint[0]}: {e}')

            except Exception as e:
                _logger.warning(f'Error during cleanup of {table}: {e}')

    cr.commit()
    _logger.info('Pre-init hook completed')


def post_init_hook(env):
    """
    Post installation hook
    """
    _logger.info('Running post_init_hook for steel_structure_project')
    _logger.info('Module installation completed successfully')