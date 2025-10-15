# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class ProjectConfirmWizard(models.TransientModel):
    """Wizard to confirm project with validation"""
    _name = 'project.confirm.wizard'
    _description = 'Confirm Project Wizard'

    project_id = fields.Many2one('steel.project', string='Project', required=True)

    # Validation checks
    has_products = fields.Boolean(string='Has Products', compute='_compute_validation')
    has_evaluation = fields.Boolean(string='Has Evaluation', compute='_compute_validation')
    has_operations = fields.Boolean(string='Has Operations', compute='_compute_validation')
    has_components = fields.Boolean(string='Has Components', compute='_compute_validation')

    validation_passed = fields.Boolean(string='Validation Passed', compute='_compute_validation')
    validation_message = fields.Text(string='Validation Message', compute='_compute_validation')

    # Confirmation options
    confirm_evaluation = fields.Boolean(string='Confirm Evaluation', default=True)
    create_operations = fields.Boolean(string='Create Operations if Missing', default=True)

    notes = fields.Text(string='Confirmation Notes')

    @api.depends('project_id')
    def _compute_validation(self):
        for wizard in self:
            project = wizard.project_id

            wizard.has_products = bool(project.product_ids)
            wizard.has_evaluation = bool(project.evaluation_ids)
            wizard.has_operations = bool(project.operation_ids)
            wizard.has_components = any(p.component_id for p in project.product_ids)

            # Build validation message
            messages = []
            if not wizard.has_products:
                messages.append("⚠️ No products defined")
            if not wizard.has_evaluation:
                messages.append("⚠️ No evaluation created")
            if not wizard.has_operations:
                messages.append("⚠️ No operations created")
            if not wizard.has_components:
                messages.append("⚠️ No components assigned to products")

            if messages:
                wizard.validation_message = "\n".join(messages)
                wizard.validation_passed = False
            else:
                wizard.validation_message = "✓ All validations passed"
                wizard.validation_passed = True

    def action_confirm_project(self):
        """Confirm project with validation"""
        self.ensure_one()

        if not self.validation_passed and not self.create_operations:
            raise UserError(
                "Project validation failed:\n\n" + self.validation_message +
                "\n\nPlease fix the issues or enable 'Create Operations if Missing'"
            )

        # Confirm evaluation if requested
        if self.confirm_evaluation and self.project_id.evaluation_ids:
            for evaluation in self.project_id.evaluation_ids:
                if evaluation.state != 'confirmed':
                    evaluation.action_confirm()

        # Create operations if missing and requested
        if self.create_operations and not self.has_operations:
            self._auto_create_operations()

        # Confirm project
        self.project_id.write({
            'state': 'confirmed',
            'date_confirmed': fields.Datetime.now(),
            'confirmed_by': self.env.user.id,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': '✓ Project Confirmed',
                'message': f'Project {self.project_id.name} confirmed successfully',
                'type': 'success',
                'sticky': False,
            }
        }

    def _auto_create_operations(self):
        """Auto create operations from project products"""
        for product in self.project_id.product_ids:
            if product.component_id and product.component_id.operation_template_ids:
                for template in product.component_id.operation_template_ids:
                    self.env['steel.project.operation'].create({
                        'project_id': self.project_id.id,
                        'product_id': product.id,
                        'component_id': product.component_id.id,
                        'operation_type_id': template.operation_type_id.id,
                        'operation_quantity': product.product_quantity,
                        'name': f"{product.name} - {template.operation_type_id.name}",
                    })