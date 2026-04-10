# res_partner.py
# Asiakkaat (Customers) logic placeholder
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    procountor_id = fields.Char(string="Procountor ID")

    def action_export_to_procountor(self):
        for p in self:
            payload = {
                "name": p.name,
                "email": p.email,
                "phone": p.phone,
                "address": p.street,
                "city": p.city,
                "zip": p.zip,
                "country": p.country_id.name,
            }
            res = self.env['procountor.api'].api_post("/businesspartners", payload)
            p.procountor_id = res.get("id")
