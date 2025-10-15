# -*- coding: utf-8 -*-
# models/steel_production_stage.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SteelProductionStage(models.Model):
    _name = 'steel.production.stage'
    _description = 'Steel Production Stage (MRP Operation)'
    _order = 'sequence, stage_name'

    # SQL CONSTRAINT: Prevent duplicate operation+part combination
    _sql_constraints = [
        ('unique_operation_per_part',
         'UNIQUE(component_id, part_id, operation_id)',
         '⚠️ This operation already exists for this part! Each operation can only be added once per part.')
    ]

    component_id = fields.Many2one(
        'steel.project.components',
        string='Component',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)

    part_id = fields.Many2one(
        'steel.product.part',
        string='Part',
        required=True,
        domain="[('component_id', '=', component_id)]",
        help='Select the part this stage is for'
    )
    part_name = fields.Char(
        string='Part Name',
        related='part_id.part_name',
        store=True,
        readonly=True
    )
    part_number = fields.Char(
        string='Part Number',
        related='part_id.part_number',
        store=True,
        readonly=True
    )

    # MRP Operation is the main reference (this is the "stage")
    operation_id = fields.Many2one(
        'mrp.routing.workcenter',
        string='MRP Operation (Stage)',
        required=True,
        help='Select the manufacturing operation that represents this production stage (e.g., Cut-1, Weld-2, Paint-1)'
    )

    stage_name = fields.Char(
        string='Stage Name',
        compute='_compute_stage_name',
        store=True,
        help='Automatically set from MRP Operation name'
    )

    stage_code = fields.Char(
        string='Stage Code',
        compute='_compute_stage_name',
        store=True
    )

    # Workcenter from the operation
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string='Workcenter',
        related='operation_id.workcenter_id',
        store=True,
        readonly=True,
        help='Workcenter automatically set from MRP Operation'
    )

    required_time = fields.Float(
        string='Required Time (Hours)',
        compute='_compute_time_from_operation',
        store=True,
        readonly=False,
        help='Time automatically calculated from MRP Operation'
    )

    # ENHANCED: Multiple Workers and Machines (Many2many)
    worker_ids = fields.Many2many(
        'hr.employee',
        'steel_stage_employee_rel',
        'stage_id',
        'employee_id',
        string='Workers',
        help='Select multiple workers for this stage'
    )

    machine_ids = fields.Many2many(
        'maintenance.equipment',
        'steel_stage_equipment_rel',
        'stage_id',
        'equipment_id',
        string='Machines',
        help='Select multiple machines/equipment for this stage'
    )

    description = fields.Text(
        string='Description',
        compute='_compute_description_from_operation',
        store=True,
        readonly=False
    )

    hourly_rate = fields.Monetary(
        string='Hourly Labor Cost',
        compute='_compute_hourly_rate_from_workcenter',
        store=True,
        readonly=False,
        currency_field='currency_id',
        help='Cost per hour - automatically set from Workcenter'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    # Computed
    estimated_labor_cost = fields.Monetary(
        string='Estimated Labor Cost',
        compute='_compute_estimated_labor_cost',
        store=True,
        currency_field='currency_id'
    )

    worker_count = fields.Integer(
        string='Workers',
        compute='_compute_counts'
    )

    machine_count = fields.Integer(
        string='Machines',
        compute='_compute_counts'
    )

    # For operation tracking
    part_ids = fields.One2many(
        'steel.product.part',
        'current_stage_id',
        string='Parts in this Stage'
    )

    # Quality control
    quality_check_required = fields.Boolean(
        string='Quality Check Required',
        default=False
    )
    quality_criteria = fields.Text(string='Quality Criteria')

    # ========================================
    # VALIDATION: Prevent Duplicate Operations
    # ========================================

    @api.constrains('component_id', 'part_id', 'operation_id')
    def _check_unique_operation_per_part(self):
        """Ensure each operation can only be added once per part"""
        for record in self:
            if record.component_id and record.part_id and record.operation_id:
                duplicate = self.search([
                    ('component_id', '=', record.component_id.id),
                    ('part_id', '=', record.part_id.id),
                    ('operation_id', '=', record.operation_id.id),
                    ('id', '!=', record.id)
                ], limit=1)

                if duplicate:
                    raise ValidationError(
                        f"❌ Duplicate Operation Detected!\n\n"
                        f"Operation '{record.operation_id.name}' already exists for part '{record.part_id.part_name}'.\n\n"
                        f"Each operation can only be added ONCE per part.\n"
                        f"If you need to modify this stage, please edit the existing one instead of creating a duplicate."
                    )

    @api.onchange('part_id', 'operation_id')
    def _onchange_check_duplicate(self):
        """Real-time duplicate check when changing part or operation"""
        if self.part_id and self.operation_id and self.component_id:
            # Check if this combination already exists
            existing = self.search([
                ('component_id', '=', self.component_id.id),
                ('part_id', '=', self.part_id.id),
                ('operation_id', '=', self.operation_id.id),
                ('id', '!=', self.id or 0)
            ], limit=1)

            if existing:
                return {
                    'warning': {
                        'title': '⚠️ Duplicate Detected',
                        'message': (
                            f"Operation '{self.operation_id.name}' already exists for part '{self.part_id.part_name}'!\n\n"
                            f"Please select a different operation or edit the existing stage."
                        )
                    }
                }

    # ========================================
    # COMPUTED FIELDS
    # ========================================

    @api.depends('operation_id', 'operation_id.name')
    def _compute_stage_name(self):
        """Stage name comes from MRP Operation name"""
        for record in self:
            if record.operation_id:
                record.stage_name = record.operation_id.name
                record.stage_code = record.operation_id.name
            else:
                record.stage_name = "New Stage"
                record.stage_code = ""

    @api.depends('operation_id', 'operation_id.time_cycle_manual')
    def _compute_time_from_operation(self):
        """Required time comes from MRP Operation"""
        for record in self:
            if record.operation_id and record.operation_id.time_cycle_manual:
                record.required_time = record.operation_id.time_cycle_manual
            elif not record.required_time:
                record.required_time = 1.0

    @api.depends('operation_id', 'operation_id.note')
    def _compute_description_from_operation(self):
        """Description comes from MRP Operation note"""
        for record in self:
            if record.operation_id and record.operation_id.note:
                record.description = record.operation_id.note
            elif not record.description:
                record.description = ""

    @api.depends('workcenter_id', 'workcenter_id.costs_hour')
    def _compute_hourly_rate_from_workcenter(self):
        """Hourly rate comes from Workcenter"""
        for record in self:
            if record.workcenter_id and record.workcenter_id.costs_hour:
                record.hourly_rate = record.workcenter_id.costs_hour
            elif not record.hourly_rate:
                record.hourly_rate = 50.0

    @api.depends('required_time', 'hourly_rate')
    def _compute_estimated_labor_cost(self):
        for record in self:
            record.estimated_labor_cost = record.required_time * record.hourly_rate

    @api.depends('worker_ids', 'machine_ids')
    def _compute_counts(self):
        for record in self:
            record.worker_count = len(record.worker_ids)
            record.machine_count = len(record.machine_ids)

    # ========================================
    # ONCHANGE METHODS
    # ========================================

    @api.onchange('operation_id')
    def _onchange_operation_id(self):
        """When MRP Operation is selected, auto-fill all related data"""
        if self.operation_id:
            # Auto-fill sequence
            if not self.sequence or self.sequence == 10:
                self.sequence = self.operation_id.sequence

            # Auto-fill time
            if self.operation_id.time_cycle_manual:
                self.required_time = self.operation_id.time_cycle_manual

            # Auto-fill description
            if self.operation_id.note:
                self.description = self.operation_id.note

    # ========================================
    # HELPER METHODS FOR MULTI-SELECT
    # ========================================

    def get_worker_names(self):
        """Get comma-separated worker names"""
        self.ensure_one()
        return ', '.join(self.worker_ids.mapped('name'))

    def get_machine_names(self):
        """Get comma-separated machine names"""
        self.ensure_one()
        return ', '.join(self.machine_ids.mapped('name'))


class SteelStageDefinition(models.Model):
    _name = 'steel.stage.definition'
    _description = 'Steel Stage Definition/Specification'
    _order = 'sequence, id'

    stage_id = fields.Many2one(
        'steel.production.stage',
        string='Production Stage',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)
    specification_name = fields.Char(string='Specification', required=True)
    specification_value = fields.Char(string='Value')
    specification_type = fields.Selection([
        ('text', 'Text'),
        ('numeric', 'Numeric'),
        ('boolean', 'Yes/No'),
        ('instruction', 'Instruction')
    ], string='Type', default='text')
    is_mandatory = fields.Boolean(string='Mandatory', default=False)
    notes = fields.Text(string='Notes')