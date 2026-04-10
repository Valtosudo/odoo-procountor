# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # --- Procountor-integraation näkyvät tilakentät (vain lukemista varten UI:ssa) ---
    procountor_external_id = fields.Char(string="Procountor ID", readonly=True, copy=False)
    procountor_last_status = fields.Char(string="Procountor status", readonly=True, copy=False)

    # -------------------------------------------------------------------------
    # Julkinen toiminto: Lähetä lasku Procountoriin (mock-tilassa ei verkkokutsua)
    # -------------------------------------------------------------------------
    def action_send_to_procountor(self):
        """
        Lähettää laskun Procountoriin käyttäen procountor.api -asiakasta.
        Mock-tilassa:
          - EI tehdä ulkoista HTTP-kutsua
          - palautetaan mock-vastaus (id/status)
          - päivitetään laskun kentät ja chatter-viesti
        """
        for move in self:
            # Varmistus: lähetetään vain myyntilaskuja (voit poistaa/tarkentaa tarpeesi mukaan)
            if move.move_type not in ('out_invoice', 'out_refund'):
                raise UserError(_("Vain myyntilaskut voidaan lähettää Procountoriin."))

            # Rakenna Procountor-payload (muokkaa tarpeittesi mukaan)
            payload = move._build_procountor_payload()

            # Kutsu API:a (mock-tilassa palauttaa mock-vastauksen)
            api = self.env['procountor.api']
            try:
                res = api.api_post("/invoices", payload)
            except Exception as e:
                _logger.exception("Procountor-kutsu epäonnistui")
                move._notify_error(_("Procountor-kutsu epäonnistui: %s") % (str(e)))
                continue

            # Odotettu onnistumisvastaus: {"status":"OK","id":<int>,"mock":True/False,...}
            if isinstance(res, dict) and res.get("status") == "OK":
                external_id = str(res.get("id") or "")
                is_mock = bool(res.get("mock"))

                move.procountor_external_id = external_id
                move.procountor_last_status = "SENT (MOCK)" if is_mock else "SENT"

                self._cr.commit()  # varmistetaan, että käyttäjä näkee muutoksen heti UI:ssa
                move._notify_success(external_id=external_id, is_mock=is_mock)
            else:
                # Virhepolku – kirjoita syy chatteriin
                message = res.get("message") if isinstance(res, dict) else str(res)
                move._notify_error(_("Procountor-lähetys epäonnistui: %s") % (message or res))
        return True

    # -------------------------------------------------------------------------
    # Payloadin muodostus (muokkaa tämän rakenteen Procountorin skeeman mukaiseksi)
    # -------------------------------------------------------------------------
    def _build_procountor_payload(self):
        """
        Rakenna Procountorille lähetettävä sanoma.
        Tämä on yksinkertaistettu esimerkki, joka riittää mock-testaukseen.
        Muokkaa/kartoita kentät vastaamaan Procountorin varsinaista skeemaa,
        kun testirajapinta/prod-rajapinta on käytettävissä.

        Palauttaa: dict (JSON-serialisoituva)
        """
        self.ensure_one()

        # Asiakastiedot
        partner = self.partner_id
        company = self.company_id

        # Laskurivit mock-tyylisesti
        rows = []
        for line in self.invoice_line_ids:
            rows.append({
                "product": line.product_id.default_code or line.product_id.name or "Tuote",
                "name": line.name or line.product_id.name or "Rivi",
                "quantity": line.quantity or 1.0,
                "unitPrice": float(line.price_unit or 0.0),
                "taxName": ", ".join(line.tax_ids.mapped('name')) if line.tax_ids else "",
                "subtotal": float(line.price_subtotal or 0.0),
            })

        payload = {
            "externalReference": self.name or self.payment_reference or (self.ref or f"INV-{self.id}"),
            "invoiceDate": fields.Date.to_string(self.invoice_date or fields.Date.context_today(self)),
            "dueDate": fields.Date.to_string(self.invoice_date_due or self.invoice_date or fields.Date.context_today(self)),
            "currency": self.currency_id.name or "EUR",

            # Asiakas
            "customer": {
                "name": partner.name or "Asiakas",
                "vat": partner.vat or "",
                "email": partner.email or "",
                "phone": partner.phone or partner.mobile or "",
                "street": partner.street or "",
                "zip": partner.zip or "",
                "city": partner.city or "",
                "country": partner.country_id.code or "",
            },

            # Yritys (lähettäjä)
            "company": {
                "name": company.name or "Yritys",
                "vat": company.vat or "",
                "street": company.street or "",
                "zip": company.zip or "",
                "city": company.city or "",
                "country": company.country_id.code or "",
                "iban": company.partner_id.bank_ids[:1].acc_number if company.partner_id.bank_ids else "",
            },

            # Summat
            "amountUntaxed": float(self.amount_untaxed),
            "amountTax": float(self.amount_tax),
            "amountTotal": float(self.amount_total),

            # Rivistö
            "rows": rows,
        }

        # Tässä voit lisätä valinnaisia avaimia (maksuehto, viivästyskorko, tms.)
        return payload

    # -------------------------------------------------------------------------
    # Ilmoitukset käyttäjälle (chatter + banner)
    # -------------------------------------------------------------------------
    def _notify_success(self, external_id, is_mock=True):
        """Kirjoita onnistumisviesti chatteriin ja näytä toast-ilmoitus."""
        self.ensure_one()
        body = _("Procountor-lähetys onnistui{mock}."
                 "<br/>ID: {id}").format(
            mock=" (MOCK)" if is_mock else "",
            id=external_id or "-"
        )
        self.message_post(body=body)

        # Näytä myös toast-ilmoitus (ei pakollinen, mutta kiva käyttäjälle)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Procountor",
                'message': _("Lähetys onnistui{mock}. ID: {id}").format(
                    mock=" (MOCK)" if is_mock else "",
                    id=external_id or "-"
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def _notify_error(self, message):
        """Kirjoita virheviesti chatteriin ja näytä punainen toast."""
        self.ensure_one()
        self.message_post(body=message or _("Procountor-lähetys epäonnistui."))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Procountor",
                'message': message or _("Procountor-lähetys epäonnistui."),
                'type': 'danger',
                'sticky': False,
            }
        }
