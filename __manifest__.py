{
    'name': 'Steel Structure Project',
    'version': '17.0.2.0.0',  # <-- Change this version
    'category': 'Project',
    'summary': 'Manage Steel Structure Projects with Material and Labor Cost Tracking',
    'description': """
        Steel Structure Project Management
        ===================================
        * Manage steel structure projects with customer integration
        * Track products, components, parts, and production stages
        * Material cost estimation and actual tracking
        * Labor cost estimation with worker and machine assignment
        * Integration with Manufacturing (MRP) workcenters and operations
        * Cost evaluation with overhead and profit calculations
        * Actual operation tracking with variance analysis
        * Dashboard and reporting capabilities
        * Compare estimated vs actual costs
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'product',
        'sale',
        'purchase',
        'stock',
        'mrp',
        'account',
        'mail',

    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',

        # Views
        'views/steel_project_views.xml',
        'views/steel_project_product_views.xml',
        'views/steel_project_components_views.xml',
        'views/steel_project_evaluation_views.xml',
        'views/steel_project_operation_views.xml',
        'views/steel_project_dashboard_views.xml',
        'views/steel_project_comparison_report_views.xml',
        'views/steel_operation_matrix_views.xml',  # ADD THIS
        'views/project_wizards_views.xml',
        # Remove this line:
        # 'wizard/steel_work_order_bulk_move_wizard_views.xml',

        # Menus (must be last)
        'views/menu_views.xml',
    ],
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'steel_structure_project/static/src/js/shopfloor_grid_widget.js',
            'steel_structure_project/static/src/xml/shopfloor_grid_widget.xml',
        ],
    },
}