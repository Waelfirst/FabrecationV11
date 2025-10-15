# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SteelProjectProduct(models.Model):
    _name = 'steel.project.product'
    _description = 'Steel Project Product'
    _order = 'sequence, id'

    project_id = fields.Many2one('steel.project', string='Project', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    name = fields.Char(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    component_id = fields.Many2one('steel.product.component', string='Component')

    product_quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                             related='product_id.uom_id', store=True)

    # Cost fields
    estimated_cost = fields.Monetary(string='Estimated Cost', compute='_compute_estimated_cost',
                                     store=True, currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', compute='_compute_actual_cost',
                                  store=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    notes = fields.Text(string='Notes')

    @api.depends('product_id', 'product_quantity', 'component_id', 'component_id.part_ids',
                 'component_id.part_ids.material_id', 'component_id.part_ids.quantity')
    def _compute_estimated_cost(self):
        for record in self:
            cost = 0.0

            # Cost from product
            if record.product_id:
                cost += record.product_id.standard_price * record.product_quantity

            # Cost from component parts
            if record.component_id:
                for part in record.component_id.part_ids:
                    if part.material_id:
                        part_cost = part.material_id.standard_price * part.quantity * record.product_quantity
                        cost += part_cost

            record.estimated_cost = cost

    @api.depends('project_id.operation_ids', 'project_id.operation_ids.actual_cost')
    def _compute_actual_cost(self):
        for record in self:
            operations = record.project_id.operation_ids.filtered(lambda o: o.product_id == record)
            record.actual_cost = sum(operations.mapped('actual_cost'))