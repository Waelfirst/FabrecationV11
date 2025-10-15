# models/steel_operation_stage.py

from odoo import models, fields, api


class SteelOperationStage(models.Model):
    _name = 'steel.operation.stage'
    _description = 'Steel Operation Stage Tracking'
    _order = 'sequence, id'

    operation_id = fields.Many2one(
        'steel.project.operation',
        string='Operation',
        required=True,
        ondelete='cascade',
        index=True
    )

    stage_id = fields.Many2one(
        'steel.production.stage',
        string='Production Stage',
        required=True,
        ondelete='restrict',
        index=True
    )

    sequence = fields.Integer(string='Sequence', default=10)
    stage_name = fields.Char(string='Stage Name', required=True)

    # Part information - properly defined related fields
    part_id = fields.Many2one(
        'steel.product.part',
        string='Part',
        related='stage_id.part_id',
        store=True,
        readonly=True
    )

    part_name = fields.Char(
        string='Part Name',
        related='stage_id.part_id.part_name',
        store=True,
        readonly=True
    )

    # Estimated vs Actual
    estimated_time = fields.Float(
        string='Estimated Time (Hours)',
        default=0.0
    )
    actual_time = fields.Float(
        string='Actual Time (Hours)',
        default=0.0
    )
    time_variance = fields.Float(
        string='Time Variance',
        compute='_compute_variance',
        store=True
    )

    estimated_cost = fields.Monetary(
        string='Estimated Labor Cost',
        default=0.0,
        currency_field='currency_id'
    )
    actual_labor_cost = fields.Monetary(
        string='Actual Labor Cost',
        compute='_compute_actual_labor_cost',
        store=True,
        currency_field='currency_id'
    )
    cost_variance = fields.Monetary(
        string='Cost Variance',
        compute='_compute_variance',
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    hourly_rate = fields.Float(string='Hourly Rate', default=50.0)

    # Workers
    worker_ids = fields.Many2many(
        'hr.employee',
        'steel_operation_stage_employee_rel',
        'operation_stage_id',
        'employee_id',
        string='Workers Assigned'
    )

    # Status
    state = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string='Status', default='pending', tracking=True)

    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    notes = fields.Text(string='Notes')

    @api.depends('actual_time', 'hourly_rate')
    def _compute_actual_labor_cost(self):
        for record in self:
            record.actual_labor_cost = record.actual_time * record.hourly_rate

    @api.depends('estimated_time', 'actual_time', 'estimated_cost', 'actual_labor_cost')
    def _compute_variance(self):
        for record in self:
            record.time_variance = record.actual_time - record.estimated_time
            record.cost_variance = record.actual_labor_cost - record.estimated_cost

    def action_start(self):
        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now()
        })

    def action_complete(self):
        self.write({
            'state': 'completed',
            'end_date': fields.Datetime.now()
        })

    def action_reset(self):
        self.write({
            'state': 'pending',
            'start_date': False,
            'end_date': False
        })