# -*- coding: utf-8 -*-
from odoo import http,_
from odoo.exceptions import AccessDenied, UserError
from odoo.addons.web.controllers.main import set_cookie_and_redirect
import urllib, json

DINGTALK_URL = "https://oapi.dingtalk.com"

class SceDingtalk(http.Controller):
    @http.route('/sce_dingtalk/oauth/script/<string:model>', auth='public')
    def oauth_script(self, model, **kw):
        # config = http.request.env['sce_dingtalk.config'].sudo().search([('res_model','=',model),('is_master','=',True)])
        model = http.request.env['ir.model'].sudo().search([('model','=',model)])
        if model:
            config = model.sce_dingtalk_config_id
        else:
            config = False
        code = http.request.params.get('code')
        target = http.request.params.get('target')
        if not config:
            return "No Dingtalk Config."
        if not code:
            return http.request.render("sce_dingtalk.oauth_script",{"corpId": config[0].corpid})
        # If open in pc, redirect to PC browser.
        if target and target=='pc' and not http.request.params.get('pcopened'):
            return http.request.render("sce_dingtalk.oauth_redirect",{"url": http.request.httprequest.url+"&pcopened=True"})
        result = self._get_userid(config, code)
        if result['errcode'] == 40014:
            config._refresh_token()
            result = self._get_userid(config, code)
        userid = result.get("userid", False)
        # Dingtalk signin
        if not userid:
            return _("Cannot get uid from dingtalk.")
        try:
            credentials = http.request.env['res.users'].sudo().auth_dingtalk_client(userid, code)
        except AccessDenied:
            return _("Not registed user, please contact administrator.")
        uid = http.request.session.authenticate(*credentials)
        if uid:
            return set_cookie_and_redirect(urllib.parse.unquote(http.request.params.get('redirect')))
        else:
            return _("Dingtalk client signin faild, please contact administrator.")


    def _get_userid(self, config, code):
        url = "%s/user/getuserinfo?access_token=%s&code=%s" % (DINGTALK_URL, config.get_token(), code)
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req).read()
        return json.loads(resp.decode())



#     @http.route('/sce_sso/sce_sso/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('sce_sso.listing', {
#             'root': '/sce_sso/sce_sso',
#             'objects': http.request.env['sce_sso.sce_sso'].search([]),
#         })

#     @http.route('/sce_sso/sce_sso/objects/<model("sce_sso.sce_sso"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('sce_sso.object', {
#             'object': obj
#         })
