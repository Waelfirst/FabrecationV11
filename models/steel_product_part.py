from odoo import models, fields, api


class SteelProductPart(models.Model):
    _name = 'steel.product.part'
    _description = 'Steel Product Part'
    _order = 'sequence, part_name'

    component_id = fields.Many2one(
        'steel.project.components',
        string='Component',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    part_name = fields.Char(string='Part Name', required=True)
    part_number = fields.Char(string='Part Number', help='Part reference number or code')
    material_id = fields.Many2one(
        'product.product',
        string='Material',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])]
    )
    quantity = fields.Float(string='Quantity per Unit', required=True, default=1.0,
                            help='Quantity needed per product unit')
    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_total_quantity',
        store=True,
        help='Total quantity = Quantity per unit × Product quantity'
    )
    product_quantity = fields.Float(
        related='component_id.product_id.quantity',
        string='Product Quantity',
        readonly=True
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='material_id.uom_id',
        readonly=True
    )
    unit_cost = fields.Float(
        string='Unit Cost',
        related='material_id.standard_price',
        readonly=True
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
    notes = fields.Text(string='Notes')

    # For operation tracking
    current_stage_id = fields.Many2one(
        'steel.production.stage',
        string='Current Stage',
        help='Current production stage of this part'
    )
    is_completed = fields.Boolean(string='Completed', default=False)

    @api.depends('quantity', 'product_quantity')
    def _compute_total_quantity(self):
        for record in self:
            record.total_quantity = record.quantity * record.product_quantity

    @api.depends('total_quantity', 'unit_cost')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = record.total_quantity * record.unit_cost