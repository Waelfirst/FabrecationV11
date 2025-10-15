# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class SteelOperationMatrix(models.TransientModel):
    """Wizard for matrix view of operations and parts"""
    _name = 'steel.operation.matrix'
    _description = 'Operation Parts Matrix View'

    project_ids = fields.Many2many('steel.project', 'steel_matrix_project_rel', 'matrix_id', 'project_id', string='Projects', required=True)
    product_ids = fields.Many2many('steel.project.product', 'steel_matrix_product_rel', 'matrix_id', 'product_id', string='Products', domain="[('project_id', 'in', project_ids)]")
    operation_filter_ids = fields.Many2many('steel.project.operation', 'steel_matrix_operation_filter_rel', 'matrix_id', 'operation_id', string='Filter by Operations', help='Select specific operations to include in matrix')
    evaluation_filter_ids = fields.Many2many('steel.project.evaluation', 'steel_matrix_evaluation_filter_rel', 'matrix_id', 'evaluation_id', string='Filter by Evaluations', help='Select specific evaluations to include')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    transaction_number = fields.Char(string='Transaction Number', default=lambda self: self.env['ir.sequence'].next_by_code('steel.operation.matrix') or 'NEW', readonly=True)
    transaction_date = fields.Datetime(string='Transaction Date', default=fields.Datetime.now, readonly=True)
    matrix_line_ids = fields.One2many('steel.operation.matrix.line', 'matrix_id', string='Matrix Lines')
    operation_ids = fields.Many2many('steel.project.operation', 'steel_matrix_operation_rel', 'matrix_id', 'operation_id', string='Operations', compute='_compute_operations', store=True)
    parts_count = fields.Integer(string='Parts Count', compute='_compute_counts')
    operations_count = fields.Integer(string='Operations Count', compute='_compute_counts')
    total_estimated_material_qty = fields.Float(string='Total Est. Material Qty', compute='_compute_totals', store=True)
    total_actual_material_qty = fields.Float(string='Total Actual Material Qty', compute='_compute_totals', store=True)
    total_estimated_material_cost = fields.Monetary(string='Total Est. Material Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    total_actual_material_cost = fields.Monetary(string='Total Actual Material Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    total_estimated_time = fields.Float(string='Total Est. Time (Hours)', compute='_compute_totals', store=True)
    total_actual_time = fields.Float(string='Total Actual Time (Hours)', compute='_compute_totals', store=True)
    variance_material_qty = fields.Float(string='Material Qty Variance', compute='_compute_totals', store=True)
    variance_material_cost = fields.Monetary(string='Material Cost Variance', compute='_compute_totals', store=True, currency_field='currency_id')
    variance_time = fields.Float(string='Time Variance', compute='_compute_totals', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    is_approved = fields.Boolean(string='Approved', default=False)
    approval_date = fields.Datetime(string='Approval Date')
    approved_by = fields.Many2one('res.users', string='Approved By')
    notes = fields.Text(string='Notes')

    @api.depends('project_ids', 'product_ids', 'operation_filter_ids', 'evaluation_filter_ids', 'date_from', 'date_to')
    def _compute_operations(self):
        for record in self:
            if record.operation_filter_ids:
                record.operation_ids = record.operation_filter_ids
            else:
                domain = [('project_id', 'in', record.project_ids.ids)]
                if record.product_ids:
                    domain.append(('product_id', 'in', record.product_ids.ids))
                if record.evaluation_filter_ids:
                    domain.append(('evaluation_id', 'in', record.evaluation_filter_ids.ids))
                if record.date_from:
                    domain.append(('start_date', '>=', record.date_from))
                if record.date_to:
                    domain.append(('start_date', '<=', record.date_to))
                operations = self.env['steel.project.operation'].search(domain)
                record.operation_ids = operations

    @api.depends('matrix_line_ids', 'operation_ids')
    def _compute_counts(self):
        for record in self:
            record.parts_count = len(record.matrix_line_ids)
            record.operations_count = len(record.operation_ids)

    @api.depends('matrix_line_ids', 'matrix_line_ids.total_estimated_qty', 'matrix_line_ids.total_actual_qty', 'matrix_line_ids.total_actual_time', 'matrix_line_ids.total_estimated_time', 'matrix_line_ids.total_estimated_cost', 'matrix_line_ids.total_actual_cost')
    def _compute_totals(self):
        for record in self:
            record.total_estimated_material_qty = sum(record.matrix_line_ids.mapped('total_estimated_qty'))
            record.total_actual_material_qty = sum(record.matrix_line_ids.mapped('total_actual_qty'))
            record.total_estimated_material_cost = sum(record.matrix_line_ids.mapped('total_estimated_cost'))
            record.total_actual_material_cost = sum(record.matrix_line_ids.mapped('total_actual_cost'))
            record.total_estimated_time = sum(record.matrix_line_ids.mapped('total_estimated_time'))
            record.total_actual_time = sum(record.matrix_line_ids.mapped('total_actual_time'))
            record.variance_material_qty = record.total_actual_material_qty - record.total_estimated_material_qty
            record.variance_material_cost = record.total_actual_material_cost - record.total_estimated_material_cost
            record.variance_time = record.total_actual_time - record.total_estimated_time

    def action_load_matrix(self):
        self.ensure_one()
        self.matrix_line_ids.unlink()
        operations = self.operation_ids
        if not operations:
            raise UserError("No operations found for selected filters")
        all_parts = {}
        for operation in operations:
            for stage in operation.operation_stage_ids:
                if stage.part_id:
                    part_key = (stage.part_id.part_name, stage.part_id.material_id.id)
                    if part_key not in all_parts:
                        all_parts[part_key] = {'record': stage.part_id, 'part_name': stage.part_id.part_name, 'part_number': stage.part_id.part_number, 'material_id': stage.part_id.material_id.id, 'material_cost': stage.part_id.material_id.standard_price}
        for operation in operations:
            if operation.component_id:
                for comp_part in operation.component_id.part_ids:
                    part_key = (comp_part.part_name, comp_part.material_id.id)
                    if part_key not in all_parts:
                        all_parts[part_key] = {'record': comp_part, 'part_name': comp_part.part_name, 'part_number': comp_part.part_number, 'material_id': comp_part.material_id.id, 'material_cost': comp_part.material_id.standard_price}
        for operation in operations:
            if operation.evaluation_id:
                for eval_part in operation.evaluation_id.evaluation_part_ids.filtered('is_active_version'):
                    part_key = (eval_part.part_name, eval_part.material_id.id)
                    if part_key not in all_parts:
                        all_parts[part_key] = {'record': eval_part, 'part_name': eval_part.part_name, 'part_number': eval_part.part_number or '', 'material_id': eval_part.material_id.id, 'material_cost': eval_part.material_id.standard_price}
        if not all_parts:
            raise UserError("No parts found!\n\nMake sure:\n1. Operations have stages generated, OR\n2. Operations have components with parts, OR\n3. Evaluations have parts defined")
        created_lines = 0
        for part_key, part_data in all_parts.items():
            line_vals = {'matrix_id': self.id, 'part_name': part_data['part_name'], 'part_number': part_data['part_number'], 'material_id': part_data['material_id'], 'unit_cost': part_data['material_cost']}
            if hasattr(part_data['record'], '_name') and part_data['record']._name == 'steel.product.part':
                line_vals['part_id'] = part_data['record'].id
            line = self.env['steel.operation.matrix.line'].create(line_vals)
            created_lines += 1
            for operation in operations:
                stages = operation.operation_stage_ids.filtered(lambda s: s.part_id and s.part_id.part_name == part_data['part_name'] and s.part_id.material_id.id == part_data['material_id'])
                actual_materials = operation.actual_material_ids.filtered(lambda m: m.material_id.id == part_data['material_id'])
                estimated_qty = 0
                estimated_time = 0
                if stages:
                    estimated_qty = operation.operation_quantity
                    estimated_time = sum(stages.mapped('estimated_time'))
                    actual_time = sum(stages.mapped('actual_time'))
                else:
                    if operation.component_id:
                        comp_part = operation.component_id.part_ids.filtered(lambda p: p.part_name == part_data['part_name'] and p.material_id.id == part_data['material_id'])
                        if comp_part:
                            estimated_qty = comp_part.quantity * operation.operation_quantity
                            estimated_time = comp_part.estimated_time if hasattr(comp_part, 'estimated_time') else 0
                    if not estimated_qty and operation.evaluation_id:
                        eval_part = operation.evaluation_id.evaluation_part_ids.filtered(lambda p: p.part_name == part_data['part_name'] and p.material_id.id == part_data['material_id'] and p.is_active_version)
                        if eval_part:
                            estimated_qty = eval_part.quantity * operation.operation_quantity
                            estimated_time = eval_part.estimated_time if hasattr(eval_part, 'estimated_time') else 0
                    actual_time = 0
                actual_qty = sum(actual_materials.mapped('consumed_quantity')) if actual_materials else 0
                material_issued = bool(actual_materials)
                estimated_cost = estimated_qty * part_data['material_cost']
                actual_cost = actual_qty * part_data['material_cost']
                cell_vals = {'matrix_line_id': line.id, 'operation_id': operation.id, 'project_id': operation.project_id.id, 'evaluation_id': operation.evaluation_id.id if operation.evaluation_id else False, 'estimated_quantity': estimated_qty, 'estimated_time': estimated_time, 'estimated_cost': estimated_cost, 'actual_quantity': actual_qty, 'actual_time': actual_time, 'actual_cost': actual_cost, 'material_issued': material_issued, 'unit_cost': part_data['material_cost']}
                if 'part_id' in line_vals:
                    cell_vals['part_id'] = line_vals['part_id']
                self.env['steel.operation.matrix.cell'].create(cell_vals)
        return {'type': 'ir.actions.act_window', 'name': 'Operation Parts Matrix', 'res_model': 'steel.operation.matrix', 'res_id': self.id, 'view_mode': 'form', 'target': 'current'}

    def action_view_matrix(self):
        self.ensure_one()
        if not self.matrix_line_ids:
            raise UserError("Please load the matrix first by clicking 'Load Matrix'")
        return {'type': 'ir.actions.act_window', 'name': f'Matrix: {len(self.matrix_line_ids)} Parts', 'res_model': 'steel.operation.matrix.line', 'view_mode': 'tree,form', 'domain': [('matrix_id', '=', self.id)], 'context': {'default_matrix_id': self.id}}

    def action_validate_actuals(self):
        self.ensure_one()
        tolerance_percent = self.env['ir.config_parameter'].sudo().get_param('steel_structure_project.actual_quantity_tolerance', default='10')
        tolerance = float(tolerance_percent) / 100
        issues = []
        for line in self.matrix_line_ids:
            for cell in line.cell_ids:
                if cell.actual_quantity > 0 and cell.estimated_quantity > 0:
                    variance_percent = ((cell.actual_quantity - cell.estimated_quantity) / cell.estimated_quantity)
                    if variance_percent > tolerance:
                        issues.append(f"⚠️ {line.part_name} in {cell.operation_name}: Actual {cell.actual_quantity} exceeds estimated {cell.estimated_quantity} by {variance_percent*100:.1f}% (limit: {tolerance*100}%)")
        if issues:
            raise UserError("Actual Quantity Validation Failed:\n\n" + "\n".join(issues))
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '✓ Validation Passed', 'message': 'All actual quantities are within acceptable tolerance', 'type': 'success', 'sticky': False}}

    def action_approve(self):
        self.ensure_one()
        if self.is_approved:
            raise UserError("This matrix is already approved")
        self.write({'is_approved': True, 'approval_date': fields.Datetime.now(), 'approved_by': self.env.user.id})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': '✓ Matrix Approved', 'message': f'Matrix {self.transaction_number} approved successfully', 'type': 'success'}}


class SteelOperationMatrixLine(models.TransientModel):
    _name = 'steel.operation.matrix.line'
    _description = 'Operation Matrix Line'

    matrix_id = fields.Many2one('steel.operation.matrix', string='Matrix', required=True, ondelete='cascade')
    part_id = fields.Many2one('steel.product.part', string='Part')
    part_name = fields.Char(string='Part Name', required=True)
    part_number = fields.Char(string='Part Number')
    material_id = fields.Many2one('product.product', string='Material')
    unit_cost = fields.Float(string='Unit Cost')
    cell_ids = fields.One2many('steel.operation.matrix.cell', 'matrix_line_id', string='Cells')
    total_estimated_qty = fields.Float(string='Total Estimated Qty', compute='_compute_totals', store=True)
    total_actual_qty = fields.Float(string='Total Actual Qty', compute='_compute_totals', store=True)
    variance_qty = fields.Float(string='Qty Variance', compute='_compute_totals', store=True)
    variance_qty_percent = fields.Float(string='Qty Variance %', compute='_compute_totals', store=True)
    total_estimated_cost = fields.Monetary(string='Total Est. Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    total_actual_cost = fields.Monetary(string='Total Actual Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    variance_cost = fields.Monetary(string='Cost Variance', compute='_compute_totals', store=True, currency_field='currency_id')
    total_estimated_time = fields.Float(string='Total Est. Time', compute='_compute_totals', store=True)
    total_actual_time = fields.Float(string='Total Actual Time', compute='_compute_totals', store=True)
    variance_time = fields.Float(string='Time Variance', compute='_compute_totals', store=True)
    cells_count = fields.Integer(string='Operations', compute='_compute_totals', store=True)
    currency_id = fields.Many2one(related='matrix_id.currency_id', string='Currency')

    @api.depends('cell_ids', 'cell_ids.estimated_quantity', 'cell_ids.actual_quantity', 'cell_ids.estimated_time', 'cell_ids.actual_time', 'cell_ids.estimated_cost', 'cell_ids.actual_cost')
    def _compute_totals(self):
        for record in self:
            record.total_estimated_qty = sum(record.cell_ids.mapped('estimated_quantity'))
            record.total_actual_qty = sum(record.cell_ids.mapped('actual_quantity'))
            record.total_estimated_cost = sum(record.cell_ids.mapped('estimated_cost'))
            record.total_actual_cost = sum(record.cell_ids.mapped('actual_cost'))
            record.total_estimated_time = sum(record.cell_ids.mapped('estimated_time'))
            record.total_actual_time = sum(record.cell_ids.mapped('actual_time'))
            record.cells_count = len(record.cell_ids)
            record.variance_qty = record.total_actual_qty - record.total_estimated_qty
            record.variance_cost = record.total_actual_cost - record.total_estimated_cost
            record.variance_time = record.total_actual_time - record.total_estimated_time
            if record.total_estimated_qty > 0:
                record.variance_qty_percent = (record.variance_qty / record.total_estimated_qty) * 100
            else:
                record.variance_qty_percent = 0


class SteelOperationMatrixCell(models.TransientModel):
    _name = 'steel.operation.matrix.cell'
    _description = 'Operation Matrix Cell'

    matrix_line_id = fields.Many2one('steel.operation.matrix.line', string='Matrix Line', required=True, ondelete='cascade')
    operation_id = fields.Many2one('steel.project.operation', string='Operation', required=True)
    project_id = fields.Many2one('steel.project', string='Project')
    evaluation_id = fields.Many2one('steel.project.evaluation', string='Evaluation')
    operation_name = fields.Char(related='operation_id.display_name', string='Operation', store=True)
    operation_state = fields.Selection(related='operation_id.state', string='Operation Status', store=True)
    part_id = fields.Many2one('steel.product.part', string='Part')
    part_name = fields.Char(related='matrix_line_id.part_name', string='Part Name', store=True)
    material_id = fields.Many2one(related='matrix_line_id.material_id', string='Material', store=True)
    unit_cost = fields.Float(string='Unit Cost')
    estimated_quantity = fields.Float(string='Estimated Qty', default=0.0)
    estimated_time = fields.Float(string='Estimated Time (Hours)', default=0.0)
    estimated_cost = fields.Monetary(string='Estimated Cost', currency_field='currency_id')
    actual_quantity = fields.Float(string='Actual Qty Used', default=0.0)
    actual_time = fields.Float(string='Actual Time (Hours)', default=0.0)
    actual_cost = fields.Monetary(string='Actual Cost', currency_field='currency_id', compute='_compute_actual_cost', store=True)
    variance_qty = fields.Float(string='Qty Variance', compute='_compute_variance', store=True)
    variance_qty_percent = fields.Float(string='Qty Variance %', compute='_compute_variance', store=True)
    variance_time = fields.Float(string='Time Variance', compute='_compute_variance', store=True)
    variance_cost = fields.Monetary(string='Cost Variance', currency_field='currency_id', compute='_compute_variance', store=True)
    material_issued = fields.Boolean(string='Material Issued', default=False)
    is_over_tolerance = fields.Boolean(string='Over Tolerance', compute='_compute_tolerance_check', store=True)
    currency_id = fields.Many2one(related='matrix_line_id.currency_id', string='Currency')
    notes = fields.Text(string='Notes')

    @api.depends('actual_quantity', 'unit_cost')
    def _compute_actual_cost(self):
        for record in self:
            record.actual_cost = record.actual_quantity * record.unit_cost

    @api.depends('estimated_quantity', 'actual_quantity', 'estimated_time', 'actual_time', 'estimated_cost', 'actual_cost')
    def _compute_variance(self):
        for record in self:
            record.variance_qty = record.actual_quantity - record.estimated_quantity
            record.variance_time = record.actual_time - record.estimated_time
            record.variance_cost = record.actual_cost - record.estimated_cost
            if record.estimated_quantity > 0:
                record.variance_qty_percent = (record.variance_qty / record.estimated_quantity) * 100
            else:
                record.variance_qty_percent = 0

    @api.depends('variance_qty_percent')
    def _compute_tolerance_check(self):
        tolerance_percent = float(self.env['ir.config_parameter'].sudo().get_param('steel_structure_project.actual_quantity_tolerance', default='10'))
        for record in self:
            if record.variance_qty_percent > tolerance_percent or record.variance_qty_percent < -tolerance_percent:
                record.is_over_tolerance = True
            else:
                record.is_over_tolerance = False

    @api.constrains('actual_quantity', 'estimated_quantity')
    def _check_actual_quantity(self):
        tolerance_percent = float(self.env['ir.config_parameter'].sudo().get_param('steel_structure_project.actual_quantity_tolerance', default='10'))
        for record in self:
            if record.actual_quantity > 0 and record.estimated_quantity > 0:
                variance_percent = ((record.actual_quantity - record.estimated_quantity) / record.estimated_quantity) * 100
                if variance_percent > tolerance_percent:
                    raise ValidationError(f"Actual quantity ({record.actual_quantity}) exceeds estimated ({record.estimated_quantity}) by {variance_percent:.1f}% which is over the allowed tolerance of {tolerance_percent}%.\n\nPart: {record.part_name}\nOperation: {record.operation_name}\nProject: {record.project_id.name if record.project_id else 'N/A'}")

    def action_move_to_operation(self):
        self.ensure_one()
        if self.estimated_quantity <= 0:
            raise UserError("No quantity available to move")
        return {'type': 'ir.actions.act_window', 'name': 'Move Quantity', 'res_model': 'steel.operation.move.wizard', 'view_mode': 'form', 'target': 'new', 'context': {'default_source_cell_id': self.id, 'default_part_id': self.part_id.id if self.part_id else False, 'default_quantity': self.estimated_quantity}}

    def action_issue_material(self):
        self.ensure_one()
        if self.material_issued:
            raise UserError("Material already issued for this part in this operation")
        if self.estimated_quantity <= 0:
            raise UserError("No quantity to issue")
        if self.actual_quantity == 0:
            self.actual_quantity = self.estimated_quantity
        self.write({'material_issued': True})
        if self.material_id:
            self.env['steel.actual.material'].create({'operation_id': self.operation_id.id, 'material_id': self.material_id.id, 'part_id': self.part_id.id if self.part_id else False, 'consumed_quantity': self.actual_quantity, 'unit_cost': self.unit_cost})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Material Issued', 'message': f'{self.actual_quantity} {self.part_name} issued in {self.operation_name}', 'type': 'success'}}

    def action_save_actual_data(self):
        self.ensure_one()
        if not self.actual_time and not self.actual_quantity:
            raise UserError("Please enter actual time or actual quantity before saving")
        stage = self.operation_id.operation_stage_ids.filtered(lambda s: s.part_id and s.part_id.part_name == self.part_name)
        if stage:
            stage.write({'actual_time': self.actual_time})
        if self.actual_quantity and self.material_id:
            actual_mat = self.operation_id.actual_material_ids.filtered(lambda m: m.material_id == self.material_id and (not m.part_id or m.part_id == self.part_id))
            if actual_mat:
                actual_mat.write({'consumed_quantity': self.actual_quantity})
            else:
                self.env['steel.actual.material'].create({'operation_id': self.operation_id.id, 'material_id': self.material_id.id, 'part_id': self.part_id.id if self.part_id else False, 'consumed_quantity': self.actual_quantity, 'unit_cost': self.unit_cost})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Data Saved', 'message': f'Actual data saved for {self.part_name}', 'type': 'success'}}


class SteelOperationMoveWizard(models.TransientModel):
    _name = 'steel.operation.move.wizard'
    _description = 'Move Quantity Between Operations'

    source_cell_id = fields.Many2one('steel.operation.matrix.cell', string='Source', required=True)
    source_operation_name = fields.Char(related='source_cell_id.operation_name', string='From Operation', readonly=True)
    target_operation_id = fields.Many2one('steel.project.operation', string='To Operation', required=True, domain="[('project_id', '=', project_id), ('id', '!=', source_operation_id)]")
    source_operation_id = fields.Many2one(related='source_cell_id.operation_id', string='Source Operation')
    part_id = fields.Many2one('steel.product.part', string='Part')
    part_name = fields.Char(related='source_cell_id.part_name', string='Part Name', readonly=True)
    project_id = fields.Many2one(related='source_cell_id.operation_id.project_id', string='Project')
    quantity = fields.Float(string='Quantity to Move', required=True, default=0.0)
    available_quantity = fields.Float(related='source_cell_id.estimated_quantity', string='Available Quantity')

    @api.constrains('quantity', 'available_quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity > record.available_quantity:
                raise ValidationError(f"Cannot move {record.quantity}. Only {record.available_quantity} available.")
            if record.quantity <= 0:
                raise ValidationError("Quantity must be greater than 0")

    def action_move(self):
        self.ensure_one()
        new_source_qty = self.source_cell_id.estimated_quantity - self.quantity
        new_source_cost = new_source_qty * self.source_cell_id.unit_cost
        self.source_cell_id.write({'estimated_quantity': new_source_qty, 'estimated_cost': new_source_cost})
        target_cell = self.env['steel.operation.matrix.cell'].search([('matrix_line_id', '=', self.source_cell_id.matrix_line_id.id), ('operation_id', '=', self.target_operation_id.id)], limit=1)
        if target_cell:
            new_target_qty = target_cell.estimated_quantity + self.quantity
            new_target_cost = new_target_qty * target_cell.unit_cost
            target_cell.write({'estimated_quantity': new_target_qty, 'estimated_cost': new_target_cost})
        else:
            self.env['steel.operation.matrix.cell'].create({'matrix_line_id': self.source_cell_id.matrix_line_id.id, 'operation_id': self.target_operation_id.id, 'project_id': self.target_operation_id.project_id.id, 'evaluation_id': self.target_operation_id.evaluation_id.id if self.target_operation_id.evaluation_id else False, 'part_id': self.part_id.id if self.part_id else False, 'estimated_quantity': self.quantity, 'unit_cost': self.source_cell_id.unit_cost, 'estimated_cost': self.quantity * self.source_cell_id.unit_cost})
        return {'type': 'ir.actions.client', 'tag': 'display_notification', 'params': {'title': 'Quantity Moved', 'message': f'{self.quantity} {self.part_name} moved from {self.source_operation_name} to {self.target_operation_id.display_name}', 'type': 'success', 'sticky': False}}