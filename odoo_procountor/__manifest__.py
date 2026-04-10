{
    'name': 'Odoo Procountor Integration',
    'version': '19.0.1.0.0',
    'author': 'Valto',
    'category': 'Accounting',
    'summary': 'Integration between Odoo and Procountor',
    'depends': ['base', 'account', 'product', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/account_move_view.xml',
    ],
    'installable': True,
    'application': False,
}
