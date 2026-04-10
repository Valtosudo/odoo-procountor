# payment_import.py
# Maksujen tuonti (Payment import) logic placeholder
from odoo import models, api
from datetime import datetime, timedelta

class PaymentImport(models.Model):
    _name = "procountor.payment.import"
    _description = "Procountor Payment Import"

    @api.model
    def cron_fetch_payments(self):
        invoices = self.env['account.move'].search([('procountor_id', '!=', False)])
        api = self.env['procountor.api']

        for inv in invoices:
            data = api.api_get(f"/invoices/{inv.procountor_id}")
            if data.get("status") == "Paid":
                if inv.payment_state != "paid":
                    inv.action_post()
                    inv.write({'payment_state': 'paid'})