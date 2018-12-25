# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessDenied
from odoo.addons import base
base.res.res_users.USER_PRIVATE_FIELDS.append('oauth_dingtalk_code')

class ResUsers(models.Model):
    _inherit = 'res.users'

    oauth_dingtalk_code = fields.Char(string='Dingtalk OAuth Code', readonly=True, copy=False)

    @api.model
    def auth_dingtalk_client(self, userid, code):
        # sce specail: login=userid@sce-re.com
        login = userid + "@sce-re.com"
        users = self.env['res.users'].sudo().search([('login','=', login),('active', '=', True)])
        if not users:
            raise AccessDenied()
        users[0].sudo().write({'oauth_dingtalk_code': code})
        self.env.cr.commit()
        return (self.env.cr.dbname, users[0].login, code)

    @api.model
    def check_credentials(self, password):
        try:
            return super(ResUsers, self).check_credentials(password)
        except AccessDenied:
            res = self.sudo().search([('id', '=', self.env.uid), ('oauth_dingtalk_code', '=', password)])
            if not res:
                raise
