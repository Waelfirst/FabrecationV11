# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools


class SteelProjectComparisonReport(models.Model):
    """Report comparing Component (Standard/Evaluation) vs Actual costs"""
    _name = 'steel.project.comparison.report'
    _description = 'Component vs Actual Comparison Report'
    _auto = False
    _rec_name = 'component_id'

    # Basic Info
    project_id = fields.Many2one('steel.project', string='Project', readonly=True)
    product_id = fields.Many2one('steel.project.product', string='Product', readonly=True)
    component_id = fields.Many2one('steel.project.components', string='Component', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)

    # Part Info
    part_id = fields.Many2one('steel.product.part', string='Part', readonly=True)
    part_name = fields.Char(string='Part Name', readonly=True)
    material_id = fields.Many2one('product.product', string='Material', readonly=True)

    # Stage Info
    stage_id = fields.Many2one('steel.production.stage', string='Stage', readonly=True)
    stage_name = fields.Char(string='Stage Name', readonly=True)

    # Standard (Component/Evaluation) Values
    standard_quantity = fields.Float(string='Standard Qty', readonly=True)
    standard_material_cost = fields.Monetary(string='Standard Material Cost', readonly=True,
                                             currency_field='currency_id')
    standard_time = fields.Float(string='Standard Time (hrs)', readonly=True)
    standard_labor_cost = fields.Monetary(string='Standard Labor Cost', readonly=True, currency_field='currency_id')
    standard_total_cost = fields.Monetary(string='Standard Total Cost', readonly=True, currency_field='currency_id')

    # Actual Values
    actual_quantity = fields.Float(string='Actual Qty', readonly=True)
    actual_material_cost = fields.Monetary(string='Actual Material Cost', readonly=True, currency_field='currency_id')
    actual_time = fields.Float(string='Actual Time (hrs)', readonly=True)
    actual_labor_cost = fields.Monetary(string='Actual Labor Cost', readonly=True, currency_field='currency_id')
    actual_total_cost = fields.Monetary(string='Actual Total Cost', readonly=True, currency_field='currency_id')

    # Variances
    quantity_variance = fields.Float(string='Qty Variance', readonly=True)
    quantity_variance_pct = fields.Float(string='Qty Variance %', readonly=True)

    material_cost_variance = fields.Monetary(string='Material Cost Variance', readonly=True,
                                             currency_field='currency_id')
    material_cost_variance_pct = fields.Float(string='Material Cost Variance %', readonly=True)

    time_variance = fields.Float(string='Time Variance (hrs)', readonly=True)
    time_variance_pct = fields.Float(string='Time Variance %', readonly=True)

    labor_cost_variance = fields.Monetary(string='Labor Cost Variance', readonly=True, currency_field='currency_id')
    labor_cost_variance_pct = fields.Float(string='Labor Cost Variance %', readonly=True)

    total_cost_variance = fields.Monetary(string='Total Cost Variance', readonly=True, currency_field='currency_id')
    total_cost_variance_pct = fields.Float(string='Total Cost Variance %', readonly=True)

    # Status
    is_over_budget = fields.Boolean(string='Over Budget', readonly=True)
    is_over_time = fields.Boolean(string='Over Time', readonly=True)

    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    def init(self):
        """Create the SQL view for the comparison report"""
        tools.drop_view_if_exists(self.env.cr, 'steel_project_comparison_report')

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW steel_project_comparison_report AS (
                WITH standard_data AS (
                    -- Get standard data from components (parts and stages)
                    SELECT
                        spc.id as component_id,
                        spc.project_id,
                        spc.product_id,
                        sp.customer_id,
                        sppart.id as part_id,
                        sppart.part_name,
                        sppart.material_id,
                        sppart.total_quantity as standard_quantity,
                        sppart.total_cost as standard_material_cost,
                        sps.id as stage_id,
                        sps.stage_name,
                        sps.required_time as standard_time,
                        sps.estimated_labor_cost as standard_labor_cost
                    FROM steel_project_components spc
                    LEFT JOIN steel_project sp ON sp.id = spc.project_id
                    LEFT JOIN steel_product_part sppart ON sppart.component_id = spc.id
                    LEFT JOIN steel_production_stage sps ON sps.part_id = sppart.id
                ),
                actual_data AS (
                    -- Get actual data from work orders (aggregated)
                    SELECT
                        spo.component_id,
                        swo.part_id,
                        swo.stage_id,
                        SUM(swo.quantity_produced) as actual_quantity,
                        SUM(swo.actual_time) as actual_time,
                        SUM(swo.actual_cost) as actual_total_cost,
                        -- Calculate actual material cost from materials used (aggregated)
                        SUM(COALESCE((
                            SELECT SUM(swom.total_cost)
                            FROM steel_work_order_material swom
                            WHERE swom.work_order_id = swo.id
                        ), 0)) as actual_material_cost,
                        -- Calculate actual labor cost
                        SUM(swo.actual_time * COALESCE(sps.hourly_rate, 50.0)) as actual_labor_cost
                    FROM steel_work_order swo
                    JOIN steel_project_operation spo ON spo.id = swo.operation_id
                    LEFT JOIN steel_production_stage sps ON sps.id = swo.stage_id
                    WHERE swo.state = 'done'
                    GROUP BY spo.component_id, swo.part_id, swo.stage_id
                )

                SELECT
                    -- Use ROW_NUMBER to create unique IDs
                    ROW_NUMBER() OVER (ORDER BY sd.component_id, sd.part_id, sd.stage_id) as id,

                    -- Basic Info
                    sd.component_id,
                    sd.project_id,
                    sd.product_id,
                    sd.customer_id,
                    sd.part_id,
                    sd.part_name,
                    sd.material_id,
                    sd.stage_id,
                    sd.stage_name,

                    -- Standard Values
                    sd.standard_quantity,
                    sd.standard_material_cost,
                    sd.standard_time,
                    sd.standard_labor_cost,
                    (COALESCE(sd.standard_material_cost, 0) + COALESCE(sd.standard_labor_cost, 0)) as standard_total_cost,

                    -- Actual Values
                    COALESCE(ad.actual_quantity, 0) as actual_quantity,
                    COALESCE(ad.actual_material_cost, 0) as actual_material_cost,
                    COALESCE(ad.actual_time, 0) as actual_time,
                    COALESCE(ad.actual_labor_cost, 0) as actual_labor_cost,
                    COALESCE(ad.actual_total_cost, 0) as actual_total_cost,

                    -- Quantity Variances
                    (COALESCE(ad.actual_quantity, 0) - COALESCE(sd.standard_quantity, 0)) as quantity_variance,
                    CASE 
                        WHEN sd.standard_quantity > 0 
                        THEN ((COALESCE(ad.actual_quantity, 0) - sd.standard_quantity) / sd.standard_quantity * 100)
                        ELSE 0
                    END as quantity_variance_pct,

                    -- Material Cost Variances
                    (COALESCE(ad.actual_material_cost, 0) - COALESCE(sd.standard_material_cost, 0)) as material_cost_variance,
                    CASE 
                        WHEN sd.standard_material_cost > 0 
                        THEN ((COALESCE(ad.actual_material_cost, 0) - sd.standard_material_cost) / sd.standard_material_cost * 100)
                        ELSE 0
                    END as material_cost_variance_pct,

                    -- Time Variances
                    (COALESCE(ad.actual_time, 0) - COALESCE(sd.standard_time, 0)) as time_variance,
                    CASE 
                        WHEN sd.standard_time > 0 
                        THEN ((COALESCE(ad.actual_time, 0) - sd.standard_time) / sd.standard_time * 100)
                        ELSE 0
                    END as time_variance_pct,

                    -- Labor Cost Variances
                    (COALESCE(ad.actual_labor_cost, 0) - COALESCE(sd.standard_labor_cost, 0)) as labor_cost_variance,
                    CASE 
                        WHEN sd.standard_labor_cost > 0 
                        THEN ((COALESCE(ad.actual_labor_cost, 0) - sd.standard_labor_cost) / sd.standard_labor_cost * 100)
                        ELSE 0
                    END as labor_cost_variance_pct,

                    -- Total Cost Variances
                    (COALESCE(ad.actual_total_cost, 0) - (COALESCE(sd.standard_material_cost, 0) + COALESCE(sd.standard_labor_cost, 0))) as total_cost_variance,
                    CASE 
                        WHEN (sd.standard_material_cost + sd.standard_labor_cost) > 0 
                        THEN ((COALESCE(ad.actual_total_cost, 0) - (sd.standard_material_cost + sd.standard_labor_cost)) / (sd.standard_material_cost + sd.standard_labor_cost) * 100)
                        ELSE 0
                    END as total_cost_variance_pct,

                    -- Status Flags
                    CASE 
                        WHEN COALESCE(ad.actual_total_cost, 0) > (COALESCE(sd.standard_material_cost, 0) + COALESCE(sd.standard_labor_cost, 0))
                        THEN TRUE
                        ELSE FALSE
                    END as is_over_budget,
                    CASE 
                        WHEN COALESCE(ad.actual_time, 0) > COALESCE(sd.standard_time, 0)
                        THEN TRUE
                        ELSE FALSE
                    END as is_over_time,

                    -- Currency
                    (SELECT currency_id FROM res_company LIMIT 1) as currency_id

                FROM standard_data sd
                LEFT JOIN actual_data ad ON ad.component_id = sd.component_id 
                    AND ad.part_id = sd.part_id 
                    AND ad.stage_id = sd.stage_id
                WHERE sd.part_id IS NOT NULL AND sd.stage_id IS NOT NULL
            )
        """)