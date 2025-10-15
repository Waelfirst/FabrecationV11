# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ProjectCreateSalesOrder(models.TransientModel):
    """Wizard to create sales order from project"""
    _name = 'project.create.sales.order'
    _description = 'Create Sales Order from Project'

    project_id = fields.Many2one('steel.project', string='Project', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
    date_order = fields.Datetime(string='Order Date', default=fields.Datetime.now)
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
    validity_date = fields.Date(string='Expiration Date')

    # Configuration
    include_evaluation = fields.Boolean(string='Include Evaluation', default=True)
    evaluation_id = fields.Many2one('steel.project.evaluation', string='Evaluation',
                                    domain="[('project_id', '=', project_id)]")
    include_components = fields.Boolean(string='Include Components', default=True)

    # Material options
    check_material_availability = fields.Boolean(string='Check Material Availability', default=True)
    auto_create_rfq = fields.Boolean(string='Auto Create RFQ for Unavailable Materials', default=True)
    reserve_materials = fields.Boolean(string='Reserve Materials on SO', default=True)

    # Preview
    line_ids = fields.One2many('project.create.sales.order.line', 'wizard_id', string='Order Lines')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    notes = fields.Text(string='Notes')

    @api.onchange('project_id', 'include_evaluation', 'evaluation_id', 'include_components')
    def _onchange_project_config(self):
        """Load lines based on configuration"""
        if not self.project_id:
            return

        self.line_ids = [(5, 0, 0)]  # Clear existing lines
        lines = []

        # From evaluation
        if self.include_evaluation and self.evaluation_id:
            for eval_part in self.evaluation_id.evaluation_part_ids.filtered('is_active_version'):
                lines.append((0, 0, {
                    'product_id': eval_part.material_id.id,
                    'name': f"{eval_part.part_name} - {eval_part.part_number}",
                    'quantity': eval_part.quantity,
                    'uom_id': eval_part.material_id.uom_id.id,
                    'price_unit': eval_part.material_id.list_price,
                    'source': 'evaluation'
                }))

        # From components
        if self.include_components:
            products = self.env['steel.project.product'].search([('project_id', '=', self.project_id.id)])
            for product in products:
                if product.component_id:
                    for part in product.component_id.part_ids:
                        lines.append((0, 0, {
                            'product_id': part.material_id.id,
                            'name': f"{part.part_name} - {product.name}",
                            'quantity': part.quantity * product.product_quantity,
                            'uom_id': part.material_id.uom_id.id,
                            'price_unit': part.material_id.list_price,
                            'source': 'component'
                        }))

        self.line_ids = lines

    @api.depends('line_ids', 'line_ids.subtotal')
    def _compute_total(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.line_ids.mapped('subtotal'))

    def action_create_sales_order(self):
        """Create sales order with material availability check"""
        self.ensure_one()

        if not self.line_ids:
            raise UserError("No order lines to create sales order")

        # Create Sales Order
        so_vals = {
            'partner_id': self.partner_id.id,
            'project_id': self.project_id.id,
            'date_order': self.date_order,
            'pricelist_id': self.pricelist_id.id if self.pricelist_id else self.partner_id.property_product_pricelist.id,
            'payment_term_id': self.payment_term_id.id if self.payment_term_id else False,
            'validity_date': self.validity_date,
            'note': self.notes,
            'order_line': []
        }

        unavailable_materials = []

        for line in self.line_ids:
            if line.include:
                # Check material availability
                available_qty = line.product_id.qty_available

                if self.check_material_availability and available_qty < line.quantity:
                    unavailable_materials.append({
                        'product': line.product_id,
                        'required': line.quantity,
                        'available': available_qty,
                        'shortage': line.quantity - available_qty
                    })

                # Add SO line
                so_vals['order_line'].append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.name,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'price_unit': line.price_unit,
                }))

        # Create Sales Order
        sale_order = self.env['sale.order'].create(so_vals)

        # Reserve materials if requested
        if self.reserve_materials:
            sale_order.action_confirm()

        # Create RFQs for unavailable materials
        rfq_ids = []
        if self.auto_create_rfq and unavailable_materials:
            rfq_ids = self._create_rfqs_for_materials(unavailable_materials)

        # Update project
        self.project_id.write({
            'sale_order_id': sale_order.id,
        })

        # Prepare result message
        message = f"Sales Order {sale_order.name} created successfully"
        if rfq_ids:
            message += f"\n{len(rfq_ids)} RFQ(s) created for unavailable materials"

        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Order Created',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'notification': {
                    'type': 'success',
                    'title': 'Sales Order Created',
                    'message': message
                }
            }
        }

    def _create_rfqs_for_materials(self, unavailable_materials):
        """Create RFQs for unavailable materials"""
        rfq_ids = []

        # Group by preferred vendor if available
        vendor_materials = {}
        for material_info in unavailable_materials:
            product = material_info['product']
            # Get preferred vendor
            vendor = product.seller_ids[0].partner_id if product.seller_ids else self.env['res.partner']

            if vendor not in vendor_materials:
                vendor_materials[vendor] = []
            vendor_materials[vendor].append(material_info)

        # Create RFQ for each vendor
        for vendor, materials in vendor_materials.items():
            if not vendor:
                # No vendor found, skip or use default
                continue

            rfq_vals = {
                'partner_id': vendor.id,
                'origin': f"Project: {self.project_id.name}",
                'date_order': fields.Datetime.now(),
                'order_line': []
            }

            for mat_info in materials:
                rfq_vals['order_line'].append((0, 0, {
                    'product_id': mat_info['product'].id,
                    'name': mat_info['product'].display_name,
                    'product_qty': mat_info['shortage'],
                    'product_uom': mat_info['product'].uom_po_id.id,
                    'price_unit': mat_info['product'].standard_price,
                    'date_planned': fields.Datetime.now(),
                }))

            rfq = self.env['purchase.order'].create(rfq_vals)
            rfq_ids.append(rfq.id)

        return rfq_ids


class ProjectCreateSalesOrderLine(models.TransientModel):
    """Lines for sales order wizard"""
    _name = 'project.create.sales.order.line'
    _description = 'Sales Order Line Preview'

    wizard_id = fields.Many2one('project.create.sales.order', string='Wizard', ondelete='cascade')
    include = fields.Boolean(string='Include', default=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    uom_id = fields.Many2one('uom.uom', string='UoM')
    price_unit = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal', compute='_compute_subtotal')
    source = fields.Selection([
        ('evaluation', 'From Evaluation'),
        ('component', 'From Component'),
        ('manual', 'Manual')
    ], string='Source')

    # Availability check
    available_qty = fields.Float(string='Available', compute='_compute_availability')
    shortage_qty = fields.Float(string='Shortage', compute='_compute_availability')
    is_available = fields.Boolean(string='Available', compute='_compute_availability')

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.depends('product_id', 'quantity')
    def _compute_availability(self):
        for line in self:
            if line.product_id:
                line.available_qty = line.product_id.qty_available
                line.shortage_qty = max(0, line.quantity - line.available_qty)
                line.is_available = line.available_qty >= line.quantity
            else:
                line.available_qty = 0
                line.shortage_qty = 0
                line.is_available = False