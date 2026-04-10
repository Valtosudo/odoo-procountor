# product.py
# Tuotteet (Products) logic placeholder
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    procountor_id = fields.Char(string="Procountor ID")

    def action_export_to_procountor(self):
        for prod in self:
            payload = {
                "name": prod.name,
                "unit": prod.uom_id.name,
                "vatPercentage": 24,
                "accountNumber": prod.property_account_income_id.code,
            }
            res = self.env['procountor.api'].api_post("/products", payload)
            prod.procountor_id = res.get("id")