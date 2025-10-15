# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SteelProject(models.Model):
    _name = 'steel.project'
    _description = 'Steel Structure Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(string='Project Name', required=True, tracking=True)
    project_code = fields.Char(string='Project Code', copy=False, readonly=True,
                               default=lambda self: 'New')

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    project_manager_id = fields.Many2one('res.users', string='Project Manager',
                                         default=lambda self: self.env.user, tracking=True)

    start_date = fields.Date(string='Start Date', tracking=True)
    end_date = fields.Date(string='End Date', tracking=True)
    date_start = fields.Date(string='Start Date', related='start_date', store=True)

    project_type = fields.Selection([
        ('building', 'Building Structure'),
        ('bridge', 'Bridge'),
        ('tower', 'Tower'),
        ('industrial', 'Industrial Structure'),
        ('other', 'Other')
    ], string='Project Type', default='building')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)

    # Financial fields - FIXED DEPENDS
    total_estimated_cost = fields.Monetary(string='Total Estimated Cost',
                                           compute='_compute_costs', store=True,
                                           currency_field='currency_id')
    total_actual_cost = fields.Monetary(string='Total Actual Cost',
                                        compute='_compute_costs', store=True,
                                        currency_field='currency_id')
    cost_variance = fields.Monetary(string='Cost Variance',
                                    compute='_compute_costs', store=True,
                                    currency_field='currency_id')

    # Relations
    product_ids = fields.One2many('steel.project.product', 'project_id', string='Products')
    operation_ids = fields.One2many('steel.project.operation', 'project_id', string='Operations')
    evaluation_ids = fields.One2many('steel.project.evaluation', 'project_id', string='Evaluations')

    # Counts
    product_count = fields.Integer(string='Products', compute='_compute_counts', store=True)
    operation_count = fields.Integer(string='Operations', compute='_compute_counts', store=True)
    evaluation_count = fields.Integer(string='Evaluations', compute='_compute_counts', store=True)

    # Additional fields
    description = fields.Text(string='Description')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    # Workflow fields
    date_confirmed = fields.Datetime(string='Confirmation Date', readonly=True)
    confirmed_by = fields.Many2one('res.users', string='Confirmed By', readonly=True)

    # Sales Order link
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')

    @api.model
    def create(self, vals):
        if vals.get('project_code', 'New') == 'New':
            vals['project_code'] = self.env['ir.sequence'].next_by_code('steel.project') or 'New'
        return super(SteelProject, self).create(vals)

    @api.depends('product_ids', 'operation_ids', 'evaluation_ids')
    def _compute_counts(self):
        for project in self:
            project.product_count = len(project.product_ids)
            project.operation_count = len(project.operation_ids)
            project.evaluation_count = len(project.evaluation_ids)

    @api.depends('product_ids.estimated_cost', 'product_ids.actual_cost',
                 'operation_ids.actual_cost')
    def _compute_costs(self):
        for project in self:
            # Estimated cost from products
            project.total_estimated_cost = sum(project.product_ids.mapped('estimated_cost'))

            # Actual cost from operations
            project.total_actual_cost = sum(project.operation_ids.mapped('actual_cost'))

            # Variance
            project.cost_variance = project.total_actual_cost - project.total_estimated_cost

    def action_view_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products',
            'res_model': 'steel.project.product',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }

    def action_view_operations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Operations',
            'res_model': 'steel.project.operation',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }

    def action_view_evaluations(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Evaluations',
            'res_model': 'steel.project.evaluation',
            'view_mode': 'tree,form',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id}
        }

    def action_set_to_draft(self):
        self.write({'state': 'draft'})