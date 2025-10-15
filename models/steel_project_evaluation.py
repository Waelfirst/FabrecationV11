# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SteelProjectEvaluation(models.Model):
    _name = 'steel.project.evaluation'
    _description = 'Steel Project Evaluation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'evaluation_date desc, id desc'

    name = fields.Char(string='Evaluation Name', required=True, tracking=True)
    evaluation_code = fields.Char(string='Evaluation Code', copy=False, readonly=True,
                                  default=lambda self: 'New')

    project_id = fields.Many2one('steel.project', string='Project', required=True,
                                 ondelete='cascade', tracking=True)
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer',
                                 store=True, readonly=True)

    evaluation_date = fields.Date(string='Evaluation Date', default=fields.Date.today,
                                  required=True, tracking=True)
    valid_until = fields.Date(string='Valid Until', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', tracking=True)

    # Parts
    evaluation_part_ids = fields.One2many('steel.evaluation.part', 'evaluation_id',
                                          string='Evaluation Parts')

    # Totals
    total_parts = fields.Integer(string='Total Parts', compute='_compute_totals', store=True)
    total_estimated_cost = fields.Monetary(string='Total Estimated Cost',
                                           compute='_compute_totals', store=True,
                                           currency_field='currency_id')
    total_weight = fields.Float(string='Total Weight (kg)', compute='_compute_totals', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    # Usage tracking
    has_parts_in_use = fields.Boolean(string='Has Parts in Use',
                                      compute='_compute_parts_in_use', store=True)
    parts_in_use_count = fields.Integer(string='Parts in Use Count',
                                        compute='_compute_parts_in_use', store=True)
    parts_in_use_message = fields.Text(string='Parts Usage Info',
                                       compute='_compute_parts_in_use')

    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        if vals.get('evaluation_code', 'New') == 'New':
            vals['evaluation_code'] = self.env['ir.sequence'].next_by_code('steel.project.evaluation') or 'New'
        return super(SteelProjectEvaluation, self).create(vals)

    @api.depends('evaluation_part_ids', 'evaluation_part_ids.is_active_version',
                 'evaluation_part_ids.quantity', 'evaluation_part_ids.estimated_cost',
                 'evaluation_part_ids.weight')
    def _compute_totals(self):
        for evaluation in self:
            active_parts = evaluation.evaluation_part_ids.filtered('is_active_version')
            evaluation.total_parts = len(active_parts)
            evaluation.total_estimated_cost = sum(active_parts.mapped('estimated_cost'))
            evaluation.total_weight = sum(active_parts.mapped('weight'))

    @api.depends('evaluation_part_ids', 'evaluation_part_ids.is_used_in_operations')
    def _compute_parts_in_use(self):
        for evaluation in self:
            parts_in_use = evaluation.evaluation_part_ids.filtered('is_used_in_operations')
            evaluation.parts_in_use_count = len(parts_in_use)
            evaluation.has_parts_in_use = bool(parts_in_use)

            if parts_in_use:
                part_names = ', '.join(parts_in_use.mapped('part_name')[:5])
                if len(parts_in_use) > 5:
                    part_names += f' and {len(parts_in_use) - 5} more'
                evaluation.parts_in_use_message = f"Parts in use: {part_names}"
            else:
                evaluation.parts_in_use_message = "No parts currently in use"

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_create_new_version(self):
        """Create new version of evaluation parts"""
        self.ensure_one()

        # Deactivate all current versions
        self.evaluation_part_ids.write({'is_active_version': False})

        # Create new versions
        new_parts = []
        for part in self.evaluation_part_ids:
            new_part_vals = {
                'evaluation_id': self.id,
                'part_name': part.part_name,
                'part_number': part.part_number,
                'material_id': part.material_id.id,
                'quantity': part.quantity,
                'weight': part.weight,
                'estimated_time': part.estimated_time,
                'estimated_cost': part.estimated_cost,
                'version': part.version + 1,
                'is_active_version': True,
                'notes': f"Version {part.version + 1} - Created from v{part.version}"
            }
            new_parts.append((0, 0, new_part_vals))

        self.write({'evaluation_part_ids': new_parts})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'New Version Created',
                'message': f'New version created with {len(self.evaluation_part_ids)} parts',
                'type': 'success',
            }
        }


class SteelEvaluationPart(models.Model):
    _name = 'steel.evaluation.part'
    _description = 'Steel Evaluation Part'
    _order = 'sequence, id'

    evaluation_id = fields.Many2one('steel.project.evaluation', string='Evaluation',
                                    required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    part_name = fields.Char(string='Part Name', required=True)
    part_number = fields.Char(string='Part Number')

    material_id = fields.Many2one('product.product', string='Material', required=True,
                                  domain=[('type', 'in', ['product', 'consu'])])

    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    weight = fields.Float(string='Weight (kg)', help='Weight per unit')

    estimated_time = fields.Float(string='Estimated Time (Hours)')
    estimated_cost = fields.Monetary(string='Estimated Cost', compute='_compute_estimated_cost',
                                     store=True, currency_field='currency_id')

    currency_id = fields.Many2one(related='evaluation_id.currency_id', string='Currency')

    # Versioning
    version = fields.Integer(string='Version', default=1)
    is_active_version = fields.Boolean(string='Active Version', default=True)

    # Usage tracking
    is_used_in_operations = fields.Boolean(string='Used in Operations',
                                           compute='_compute_usage', store=True)
    operations_using_part = fields.Many2many('steel.project.operation',
                                             compute='_compute_usage',
                                             string='Operations Using This Part')

    notes = fields.Text(string='Notes')

    @api.depends('material_id', 'quantity', 'material_id.standard_price')
    def _compute_estimated_cost(self):
        for part in self:
            if part.material_id and part.quantity:
                part.estimated_cost = part.material_id.standard_price * part.quantity
            else:
                part.estimated_cost = 0.0

    @api.depends('evaluation_id.project_id.operation_ids',
                 'evaluation_id.project_id.operation_ids.evaluation_id')
    def _compute_usage(self):
        for part in self:
            operations = self.env['steel.project.operation'].search([
                ('evaluation_id', '=', part.evaluation_id.id),
                ('project_id', '=', part.evaluation_id.project_id.id)
            ])
            part.operations_using_part = operations
            part.is_used_in_operations = bool(operations)