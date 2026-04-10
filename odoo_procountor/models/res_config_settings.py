from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    procountor_mock_mode = fields.Boolean(
        string="Procountor MOCK-tila",
        help="Kun tämä on päällä, kaikki Procountor-kutsut korvataan mock-vastauksilla.",
        config_parameter="procountor.mock_mode"
    )
