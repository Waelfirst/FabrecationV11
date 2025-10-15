# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SteelProjectOperation(models.Model):
    _name = 'steel.project.operation'
    _description = 'Steel Project Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, start_date, id'

    name = fields.Char(string='Operation Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)

    project_id = fields.Many2one('steel.project', string='Project', required=True,
                                 ondelete='cascade', tracking=True)
    partner_id = fields.Many2one(related='project_id.partner_id', string='Customer',
                                 store=True, readonly=True)

    product_id = fields.Many2one('steel.project.product', string='Product',
                                 domain="[('project_id', '=', project_id)]")
    component_id = fields.Many2one('steel.product.component', string='Component')
    evaluation_id = fields.Many2one('steel.project.evaluation', string='Evaluation',
                                    domain="[('project_id', '=', project_id)]")

    operation_type_id = fields.Many2one('steel.operation.type', string='Operation Type')

    operation_quantity = fields.Float(string='Quantity', default=1.0, required=True)

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', tracking=True)

    # Stages
    operation_stage_ids = fields.One2many('steel.operation.stage', 'operation_id',
                                          string='Operation Stages')

    # Materials
    actual_material_ids = fields.One2many('steel.actual.material', 'operation_id',
                                          string='Actual Materials Used')

    # Costs
    estimated_cost = fields.Monetary(string='Estimated Cost', compute='_compute_costs',
                                     store=True, currency_field='currency_id')
    actual_cost = fields.Monetary(string='Actual Cost', compute='_compute_costs',
                                  store=True, currency_field='currency_id')
    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_costs',
                                    store=True, currency_field='currency_id')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    # Work order link
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order')

    notes = fields.Text(string='Notes')

    @api.depends('operation_stage_ids', 'operation_stage_ids.estimated_cost',
                 'actual_material_ids', 'actual_material_ids.total_cost')
    def _compute_costs(self):
        for operation in self:
            operation.estimated_cost = sum(operation.operation_stage_ids.mapped('estimated_cost'))
            operation.actual_cost = sum(operation.actual_material_ids.mapped('total_cost'))
            operation.cost_variance = operation.actual_cost - operation.estimated_cost

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_start(self):
        self.write({
            'state': 'in_progress',
            'start_date': fields.Date.today()
        })

    def action_done(self):
        self.write({
            'state': 'done',
            'end_date': fields.Date.today()
        })

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_set_to_draft(self):
        self.write({'state': 'draft'})

    def action_generate_stages(self):
        """Generate operation stages from component or evaluation"""
        self.ensure_one()

        if self.operation_stage_ids:
            raise UserError("Stages already exist. Delete them first if you want to regenerate.")

        stages = []

        # From component
        if self.component_id:
            for part in self.component_id.part_ids:
                stage_vals = {
                    'operation_id': self.id,
                    'part_id': part.id,
                    'stage_name': f"{part.part_name} - {self.operation_type_id.name if self.operation_type_id else 'Process'}",
                    'estimated_quantity': part.quantity * self.operation_quantity,
                    'estimated_time': part.estimated_time if hasattr(part, 'estimated_time') else 0,
                }
                stages.append((0, 0, stage_vals))

        # From evaluation
        elif self.evaluation_id:
            for eval_part in self.evaluation_id.evaluation_part_ids.filtered('is_active_version'):
                stage_vals = {
                    'operation_id': self.id,
                    'stage_name': f"{eval_part.part_name} - {self.operation_type_id.name if self.operation_type_id else 'Process'}",
                    'estimated_quantity': eval_part.quantity * self.operation_quantity,
                    'estimated_time': eval_part.estimated_time,
                }
                stages.append((0, 0, stage_vals))

        if stages:
            self.write({'operation_stage_ids': stages})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Stages Generated',
                    'message': f'{len(stages)} stages created successfully',
                    'type': 'success',
                }
            }
        else:
            raise UserError("No component or evaluation found to generate stages from")


class SteelOperationStage(models.Model):
    _name = 'steel.operation.stage'
    _description = 'Operation Stage'
    _order = 'sequence, id'

    operation_id = fields.Many2one('steel.project.operation', string='Operation',
                                   required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)

    stage_name = fields.Char(string='Stage Name', required=True)
    part_id = fields.Many2one('steel.product.part', string='Part')

    estimated_quantity = fields.Float(string='Estimated Quantity', default=1.0)
    estimated_time = fields.Float(string='Estimated Time (Hours)')
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')

    actual_quantity = fields.Float(string='Actual Quantity')
    actual_time = fields.Float(string='Actual Time (Hours)')
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id')

    currency_id = fields.Many2one(related='operation_id.currency_id', string='Currency')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='State', default='pending')

    notes = fields.Text(string='Notes')

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})


class SteelOperationType(models.Model):
    _name = 'steel.operation.type'
    _description = 'Steel Operation Type'
    _order = 'sequence, name'

    name = fields.Char(string='Operation Type', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)

    description = fields.Text(string='Description')

    active = fields.Boolean(string='Active', default=True)