
from odoo import models, fields

class ForceDeliveryWizard(models.TransientModel):
    _name = 'force.delivery.wizard'
    _description = 'Force Delivery Wizard'

    insufficient_products = fields.Text('Insufficient Stock Products', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking',  help="Select the picking to force delivery.")

    def action_force_delivery(self):
        # This method is called to force the delivery and invoice of sale orders
        picking = self.picking_id
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
        picking.button_validate()
        sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        return sale_orders._force_delivery_and_invoice()
