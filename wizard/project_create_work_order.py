# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProjectCreateWorkOrder(models.TransientModel):
    """Wizard to create work orders from project"""
    _name = 'project.create.work.order'
    _description = 'Create Work Order from Project'

    project_id = fields.Many2one('steel.project', string='Project', required=True)

    # Work order configuration
    name = fields.Char(string='Work Order Name')
    responsible_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    date_planned_start = fields.Datetime(string='Planned Start', default=fields.Datetime.now)
    date_planned_finished = fields.Datetime(string='Planned End')

    # What to include
    create_from_operations = fields.Boolean(string='Create from Operations', default=True)
    operation_ids = fields.Many2many('steel.project.operation', string='Operations',
                                     domain="[('project_id', '=', project_id)]")

    # Matrix configuration
    create_matrix = fields.Boolean(string='Create Actual Matrix for Tracking', default=True)
    matrix_auto_load = fields.Boolean(string='Auto Load Matrix', default=True)

    # Work center
    workcenter_id = fields.Many2one('mrp.workcenter', string='Work Center')

    notes = fields.Text(string='Notes')

    @api.onchange('project_id')
    def _onchange_project(self):
        """Load operations when project changes"""
        if self.project_id:
            self.name = f"WO - {self.project_id.name}"
            operations = self.env['steel.project.operation'].search([
                ('project_id', '=', self.project_id.id),
                ('state', 'in', ['draft', 'confirmed'])
            ])
            self.operation_ids = operations

    def action_create_work_order(self):
        """Create work orders and optional matrix"""
        self.ensure_one()

        if not self.operation_ids:
            raise UserError("Please select at least one operation")

        work_orders = []
        matrix_id = False

        # Create work orders for each operation
        for operation in self.operation_ids:
            wo_vals = {
                'name': f"{self.name} - {operation.display_name}",
                'product_id': operation.product_id.product_id.id if operation.product_id else False,
                'workcenter_id': self.workcenter_id.id if self.workcenter_id else False,
                'date_planned_start': self.date_planned_start,
                'date_planned_finished': self.date_planned_finished,
                'project_id': self.project_id.id,
                'operation_id': operation.id,
                'user_id': self.responsible_id.id,
                'note': self.notes,
            }

            # Create manufacturing order if needed
            if operation.product_id:
                mo = self._create_manufacturing_order(operation)
                wo_vals['production_id'] = mo.id

            wo = self.env['mrp.workorder'].create(wo_vals)
            work_orders.append(wo.id)

            # Update operation
            operation.write({
                'workorder_id': wo.id,
                'state': 'in_progress'
            })

        # Create matrix for tracking actuals
        if self.create_matrix:
            matrix_id = self._create_tracking_matrix()

        # Prepare return action
        if len(work_orders) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Work Order Created',
                'res_model': 'mrp.workorder',
                'res_id': work_orders[0],
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            action = {
                'type': 'ir.actions.act_window',
                'name': f'{len(work_orders)} Work Orders Created',
                'res_model': 'mrp.workorder',
                'view_mode': 'tree,form',
                'domain': [('id', 'in', work_orders)],
                'target': 'current',
            }

            if matrix_id:
                action['context'] = {
                    'notification': {
                        'type': 'success',
                        'title': 'Work Orders Created',
                        'message': f'{len(work_orders)} work orders and tracking matrix created',
                        'links': [{
                            'label': 'Open Matrix',
                            'url': f'/web#id={matrix_id}&model=steel.operation.matrix&view_type=form'
                        }]
                    }
                }

            return action

    def _create_manufacturing_order(self, operation):
        """Create manufacturing order for operation"""
        mo_vals = {
            'product_id': operation.product_id.product_id.id,
            'product_qty': operation.operation_quantity,
            'product_uom_id': operation.product_id.product_id.uom_id.id,
            'origin': f"Project: {self.project_id.name}",
            'date_planned_start': self.date_planned_start,
            'user_id': self.responsible_id.id,
        }

        mo = self.env['mrp.production'].create(mo_vals)
        return mo

    def _create_tracking_matrix(self):
        """Create operation matrix for tracking actuals"""
        matrix_vals = {
            'project_ids': [(6, 0, [self.project_id.id])],
            'operation_filter_ids': [(6, 0, self.operation_ids.ids)],
            'notes': f"Auto-created for work orders: {self.name}"
        }

        matrix = self.env['steel.operation.matrix'].create(matrix_vals)

        # Auto load if requested
        if self.matrix_auto_load:
            matrix.action_load_matrix()

        return matrix.id