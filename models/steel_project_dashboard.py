from odoo import models, fields, api, tools


class SteelProjectDashboard(models.Model):
    _name = 'steel.project.dashboard'
    _description = 'Steel Project Dashboard and Analytics'
    _auto = False
    _rec_name = 'project_id'

    # Project Info
    project_id = fields.Many2one('steel.project', string='Project', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    project_state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Project Status', readonly=True)

    # Product Info
    product_count = fields.Integer(string='Products', readonly=True)
    total_product_quantity = fields.Float(string='Total Product Qty', readonly=True)

    # Parts Analysis
    total_parts = fields.Integer(string='Total Parts', readonly=True)
    total_parts_quantity = fields.Float(string='Total Parts Qty', readonly=True)

    # Material Costs
    estimated_material_cost = fields.Monetary(string='Estimated Material Cost', readonly=True)
    actual_material_cost = fields.Monetary(string='Actual Material Cost', readonly=True)
    material_variance = fields.Monetary(string='Material Variance', readonly=True)
    material_variance_pct = fields.Float(string='Material Variance %', readonly=True)

    # Labor Costs
    estimated_labor_cost = fields.Monetary(string='Estimated Labor Cost', readonly=True)
    actual_labor_cost = fields.Monetary(string='Actual Labor Cost', readonly=True)
    labor_variance = fields.Monetary(string='Labor Variance', readonly=True)
    labor_variance_pct = fields.Float(string='Labor Variance %', readonly=True)

    # Time Analysis
    estimated_hours = fields.Float(string='Estimated Hours', readonly=True)
    actual_hours = fields.Float(string='Actual Hours', readonly=True)
    time_variance = fields.Float(string='Time Variance (Hours)', readonly=True)
    time_variance_pct = fields.Float(string='Time Variance %', readonly=True)

    # Stage Analysis
    total_stages = fields.Integer(string='Total Stages', readonly=True)
    completed_stages = fields.Integer(string='Completed Stages', readonly=True)
    progress_percentage = fields.Float(string='Progress %', readonly=True)

    # Financial Summary
    total_estimated_cost = fields.Monetary(string='Total Estimated Cost', readonly=True)
    total_actual_cost = fields.Monetary(string='Total Actual Cost', readonly=True)
    final_quote = fields.Monetary(string='Final Quote', readonly=True)
    profit_margin = fields.Monetary(string='Expected Profit', readonly=True)
    actual_profit = fields.Monetary(string='Actual Profit', readonly=True)

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    # Dates
    start_date = fields.Date(string='Start Date', readonly=True)
    end_date = fields.Date(string='End Date', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'steel_project_dashboard')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW steel_project_dashboard AS (
                SELECT 
                    sp.id,
                    sp.id as project_id,
                    sp.customer_id,
                    sp.state as project_state,
                    sp.start_date,
                    sp.end_date,

                    -- Product counts
                    COUNT(DISTINCT spp.id) as product_count,
                    COALESCE(SUM(spp.quantity), 0) as total_product_quantity,

                    -- Parts analysis
                    COUNT(DISTINCT sppart.id) as total_parts,
                    COALESCE(SUM(sppart.total_quantity), 0) as total_parts_quantity,

                    -- Material costs
                    COALESCE(SUM(sppart.total_cost), 0) as estimated_material_cost,
                    COALESCE(SUM(sam.total_cost), 0) as actual_material_cost,
                    COALESCE(SUM(sam.total_cost), 0) - COALESCE(SUM(sppart.total_cost), 0) as material_variance,
                    CASE 
                        WHEN COALESCE(SUM(sppart.total_cost), 0) > 0 
                        THEN ((COALESCE(SUM(sam.total_cost), 0) - COALESCE(SUM(sppart.total_cost), 0)) / COALESCE(SUM(sppart.total_cost), 0)) * 100
                        ELSE 0 
                    END as material_variance_pct,

                    -- Labor costs
                    COALESCE(SUM(sps.estimated_labor_cost), 0) as estimated_labor_cost,
                    COALESCE(SUM(sos.actual_labor_cost), 0) as actual_labor_cost,
                    COALESCE(SUM(sos.actual_labor_cost), 0) - COALESCE(SUM(sps.estimated_labor_cost), 0) as labor_variance,
                    CASE 
                        WHEN COALESCE(SUM(sps.estimated_labor_cost), 0) > 0 
                        THEN ((COALESCE(SUM(sos.actual_labor_cost), 0) - COALESCE(SUM(sps.estimated_labor_cost), 0)) / COALESCE(SUM(sps.estimated_labor_cost), 0)) * 100
                        ELSE 0 
                    END as labor_variance_pct,

                    -- Time analysis
                    COALESCE(SUM(sps.required_time), 0) as estimated_hours,
                    COALESCE(SUM(sos.actual_time), 0) as actual_hours,
                    COALESCE(SUM(sos.actual_time), 0) - COALESCE(SUM(sps.required_time), 0) as time_variance,
                    CASE 
                        WHEN COALESCE(SUM(sps.required_time), 0) > 0 
                        THEN ((COALESCE(SUM(sos.actual_time), 0) - COALESCE(SUM(sps.required_time), 0)) / COALESCE(SUM(sps.required_time), 0)) * 100
                        ELSE 0 
                    END as time_variance_pct,

                    -- Stage progress
                    COUNT(DISTINCT sps.id) as total_stages,
                    COUNT(DISTINCT CASE WHEN sos.state = 'completed' THEN sos.id END) as completed_stages,
                    CASE 
                        WHEN COUNT(DISTINCT sps.id) > 0 
                        THEN (COUNT(DISTINCT CASE WHEN sos.state = 'completed' THEN sos.id END)::float / COUNT(DISTINCT sps.id)::float) * 100
                        ELSE 0 
                    END as progress_percentage,

                    -- Financial summary
                    COALESCE(SUM(sppart.total_cost), 0) + COALESCE(SUM(sps.estimated_labor_cost), 0) as total_estimated_cost,
                    COALESCE(SUM(sam.total_cost), 0) + COALESCE(SUM(sos.actual_labor_cost), 0) as total_actual_cost,
                    COALESCE(MAX(spe.final_quote), 0) as final_quote,
                    COALESCE(MAX(spe.profit_amount), 0) as profit_margin,
                    COALESCE(MAX(spe.final_quote), 0) - (COALESCE(SUM(sam.total_cost), 0) + COALESCE(SUM(sos.actual_labor_cost), 0)) as actual_profit,

                    (SELECT currency_id FROM res_company LIMIT 1) as currency_id

                FROM steel_project sp
                LEFT JOIN steel_project_product spp ON spp.project_id = sp.id
                LEFT JOIN steel_project_components spc ON spc.project_id = sp.id
                LEFT JOIN steel_product_part sppart ON sppart.component_id = spc.id
                LEFT JOIN steel_production_stage sps ON sps.component_id = spc.id
                LEFT JOIN steel_project_evaluation spe ON spe.project_id = sp.id
                LEFT JOIN steel_project_operation spo ON spo.project_id = sp.id
                LEFT JOIN steel_operation_stage sos ON sos.operation_id = spo.id
                LEFT JOIN steel_actual_material sam ON sam.operation_id = spo.id

                GROUP BY sp.id, sp.customer_id, sp.state, sp.start_date, sp.end_date
            )
        """)