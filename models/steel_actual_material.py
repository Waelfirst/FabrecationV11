# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SteelActualMaterial(models.Model):
    _name = 'steel.actual.material'
    _description = 'Actual Materials Used in Operations'
    _rec_name = 'material_id'

    operation_id = fields.Many2one(
        'steel.project.operation',
        string='Operation',
        required=True,
        ondelete='cascade'
    )

    material_id = fields.Many2one(
        'product.product',
        string='Material',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])]
    )

    part_id = fields.Many2one(
        'steel.product.part',
        string='Part',
        help='Related part if applicable'
    )

    consumed_quantity = fields.Float(
        string='Consumed Quantity',
        required=True,
        default=0.0,
        help='Actual quantity of material consumed'
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='material_id.uom_id',
        readonly=True,
        store=True
    )

    unit_cost = fields.Float(
        string='Unit Cost',
        required=True,
        default=0.0
    )

    total_cost = fields.Monetary(
        string='Total Cost',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    date_used = fields.Date(
        string='Date Used',
        default=fields.Date.today
    )

    # Alias for date_used to support views that might use different names
    usage_date = fields.Date(
        string='Usage Date',
        related='date_used',
        store=True
    )

    notes = fields.Text(string='Notes')

    @api.depends('consumed_quantity', 'unit_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.consumed_quantity * record.unit_cost

    @api.onchange('material_id')
    def _onchange_material_id(self):
        """Auto-fill unit cost from material"""
        if self.material_id:
            self.unit_cost = self.material_id.standard_price