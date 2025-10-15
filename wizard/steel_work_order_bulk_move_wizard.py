# -*- coding: utf-8 -*-
# wizard/steel_work_order_bulk_move_wizard.py

from odoo import models, fields, api
from odoo.exceptions import UserError


class SteelWorkOrderBulkMoveWizard(models.TransientModel):
    """Wizard for moving multiple work orders to a new stage"""
    _name = 'steel.work.order.bulk.move.wizard'
    _description = 'Bulk Move Work Orders Wizard'

    work_order_ids = fields.Many2many(
        'steel.work.order',
        string='Work Orders',
        required=True
    )
    work_order_count = fields.Integer(
        string='Number of Parts',
        compute='_compute_work_order_count'
    )
    current_stage_id = fields.Many2one(
        'steel.production.stage',
        string='Current Stage',
        compute='_compute_current_stage'
    )
    target_stage_id = fields.Many2one(
        'steel.production.stage',
        string='Move To Stage',
    )
    target_operation_id = fields.Many2one(
        'steel.project.operation',
        string='Move To Operation',
        help='Move selected parts to another operation'
    )

    # Time update options
    update_time = fields.Boolean(
        string='Update Time',
        default=False,
        help='Add additional time to all selected parts'
    )
    additional_time = fields.Float(
        string='Additional Time (hours)',
        default=0.0
    )

    # Worker assignment options
    update_workers = fields.Boolean(
        string='Assign Workers',
        default=False
    )
    worker_ids = fields.Many2many(
        'hr.employee',
        'steel_wizard_employee_rel',
        'wizard_id',
        'employee_id',
        string='Workers'
    )

    notes = fields.Text(string='Notes')

    @api.depends('work_order_ids')
    def _compute_work_order_count(self):
        for wizard in self:
            wizard.work_order_count = len(wizard.work_order_ids)

    @api.depends('work_order_ids')
    def _compute_current_stage(self):
        for wizard in self:
            if wizard.work_order_ids:
                stages = wizard.work_order_ids.mapped('stage_id')
                if stages:
                    wizard.current_stage_id = stages[0]
                else:
                    wizard.current_stage_id = False
            else:
                wizard.current_stage_id = False

    def action_move_parts(self):
        """Move all selected work orders to target stage or operation"""
        self.ensure_one()

        if not self.work_order_ids:
            raise UserError("No work orders selected!")

        # Validate destination
        if not self.target_stage_id and not self.target_operation_id:
            raise UserError("Please select a target Stage or a target Operation!")
        if self.target_stage_id and self.target_operation_id:
            raise UserError("Please select either a Stage or an Operation, not both.")

        # Optional time and worker updates applied in both move modes
        if self.update_time and self.additional_time:
            for work_order in self.work_order_ids:
                work_order.actual_time += self.additional_time

        vals_common = {}
        if self.update_workers and self.worker_ids:
            vals_common['worker_ids'] = [(6, 0, self.worker_ids.ids)]

        # Move by Operation
        if self.target_operation_id:
            for work_order in self.work_order_ids:
                old_operation = work_order.operation_id
                # triggers write override to record estimated time/material and mark done
                work_order.write({**vals_common, 'operation_id': self.target_operation_id.id})

                msg = f"Moved to operation: {self.target_operation_id.display_name}"
                if self.notes:
                    msg += f"\nNotes: {self.notes}"
                work_order.message_post(body=msg)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Parts Moved Successfully',
                    'message': f"{len(self.work_order_ids)} part(s) moved to operation '{self.target_operation_id.display_name}'",
                    'type': 'success',
                    'sticky': False,
                }
            }

        # Move by Stage
        if self.target_stage_id:
            vals_stage = {**vals_common, 'stage_id': self.target_stage_id.id}
            self.work_order_ids.write(vals_stage)

            for work_order in self.work_order_ids:
                message = f"Moved to stage: {self.target_stage_id.stage_name}"
                if self.notes:
                    message += f"\nNotes: {self.notes}"
                work_order.message_post(body=message)

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Parts Moved Successfully',
                    'message': f"{len(self.work_order_ids)} part(s) moved to stage '{self.target_stage_id.stage_name}'",
                    'type': 'success',
                    'sticky': False,
                }
            }