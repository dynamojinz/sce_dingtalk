# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

import urllib.request
import json

DINGTALK_URL = "https://oapi.dingtalk.com"

class DingtalkLog(models.Model):
    _name = 'sce_dingtalk.log'
    _order = 'write_date desc'

    name = fields.Char()
    request = fields.Char()
    data = fields.Char()
    response = fields.Char()
    config_id = fields.Many2one('sce_dingtalk.config')

class Dingtalk(models.Model):
    _name = 'sce_dingtalk.config'

    name = fields.Char()
    token = fields.Char()
    corpid = fields.Char()
    agentid = fields.Integer()
    corpsecret = fields.Char()
    is_master = fields.Boolean(default=False)
    linkurl_format = fields.Char()
    qrcode_image = fields.Binary("2-dimention code", attachment=True, help="This field holds 2-dimention code of dingtalk plugin")
    log_ids = fields.One2many('sce_dingtalk.log', 'config_id')
    res_model_id = fields.Many2one('ir.model', 'Related Model', index=True)
    res_model = fields.Char(string='Resource Model', related='res_model_id.model', store=True, index=True, readonly=True)
    res_model_ids = fields.One2many('ir.model', 'sce_dingtalk_config_id', string='Related Model', index=True)
    test_user = fields.Char()
    test_mode = fields.Boolean(default=True)

    def get_token(self):
        if not self.token:
            self._refresh_token()
        return self.token

    def get_linkurl(self, model, redirect, target):
        if self.linkurl_format:
            # print(3)
            # print(self.linkurl_format)
            return self.linkurl_format % {
                    'model': model,
                    'redirect': urllib.parse.quote(redirect),
                    'target': target,
                    }
        else:
            # print(4)
            return redirect

    def _get_userid(self, authcode):
        url = "%s/user/getuserinfo?access_token=%s&code=%s" % (DINGTALK_URL, self.get_token(), authcode)
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req).read()
        return json.loads(resp.decode())

    def get_userid(self, authcode):
        result = self._get_userid(authcode)
        # print(result)
        if result['errcode'] == 40014:
            self._refresh_token()
            result = self._get_userid(authcode)
        if result['errcode'] == 60020:
            print('如果使用按部门授权CorpSecret，请检查该CorpSecret的配置ip地址是否和请求ip地址一致')
        return result.get("userid", False)

    def get_userinfo(self, userid):
        url = "%s/user/get?access_token=%s&userid=%s" % (DINGTALK_URL, self.get_token(), userid)
        req = urllib.request.Request(url)
        req.add_header('Content-Type', 'application/json')
        resp = urllib.request.urlopen(req).read()
        return json.loads(resp.decode())


    def send_message(self, user, message):
        raw_message = self._form_message(user, message)
        return self._send_data(user, raw_message)

    def send_action_card_message(self, user, title, markdown, url):
        raw_message = self._form_action_card_message(user, title, markdown, url)
        return self._send_data(user, raw_message)

    def _send_data(self, user, raw_message):
        error_code = self._asyn_send_message(raw_message)
        # if error_code==40014:  # access_token expired
        if error_code==88:  # access_token expired
            self._refresh_token()
            error_code = self._asyn_send_message(raw_message)
        if error_code == 0:
            return 'Success'
        else:
            return 'Failed'

    def action_test(self):
        # print(1)
        # print(self.env.user)
        # logins = self.env.user.login.split('@')
        # logins = "manager7560@sce-re.com".split('@')
        # if logins[-1]=='sce-re.com':
        # print(self.test_user)
        if self.test_user:
            message = _("Test message from SCE corporation at %s" % fields.Datetime.now())
            self.sudo().send_message(self.test_user, message)

    #--------------------------------
    # 更新token 
    #--------------------------------
    def _refresh_token(self):
        if self.corpid and self.corpsecret:
            token_url = '%s/gettoken?corpid=%s&corpsecret=%s' % (DINGTALK_URL, self.corpid, self.corpsecret)
            token_req = urllib.request.Request(token_url)
            token_req.add_header('Content-Type', 'application/json')
            token_resp = urllib.request.urlopen(token_req).read().decode()
            self._write_log('GET_TOKEN', token_url, '', token_resp)
            self.token = json.loads(token_resp)['access_token']
    #--------------------------------
    # 记录与钉钉服务器通信日志
    #--------------------------------
    def _write_log(self, name, request, data, response):
        self.env['sce_dingtalk.log'].sudo().create({
            'config_id': self.id,
            'name': name,
            'request': request,
            'data': data,
            'response': response})
    #--------------------------------
    # 构建告警信息json
    #--------------------------------
    def _form_message(self, user, msg):
        # print(2)
        values = {
            "userid_list": user,
            "msgtype": 'text',
            "agent_id": self.agentid,
            "msgcontent": {'content': msg}
            }
        msges=(bytes(json.dumps(values), 'utf-8'))
        return msges

    def _form_action_card_message(self, user, title, markdown, url):
        values = {
            "agent_id": self.agentid,
            "userid_list": user,
            "msgtype": "action_card",
            "msgcontent":{
                "title": title,
                "markdown": markdown,
                "single_title": _("View Details"),
                "single_url": url,
                # "single_url": "eapp://pages/index/index?query",
                },
            }
        msges=(bytes(json.dumps(values), 'utf-8'))
        # print(5)
        # print(msges)
        return msges

    def _asyn_send_message(self, data):
        send_url = "%s/topapi/message/corpconversation/asyncsend?access_token_v2=%s" % (DINGTALK_URL, self.get_token())
        request = urllib.request.Request(url=send_url,data=data)
        request.add_header('Content-Type', 'application/json')
        response = urllib.request.urlopen(request).read()
        # print(response.decode())
        self._write_log('SEND_MESSAGE', send_url, data, response)
        x = json.loads(response.decode())['errcode']
        # print(x)
        return x

class DingtalkMixin(models.Model):
    _name = 'sce_dingtalk.mixin'

    @api.model
    def dingtalk_send_message(self, users, message):
        # print(111)
        config = self.env['sce_dingtalk.config'].search([('res_model_ids','=',self._name),('is_master','=',True)])
        # print(config)
        if config:
            config = config[0]
            # print(config)
            config.send_message(users, message)
        else:
            print("Cannot find configuration for model:%s" % (self._name,))

    # @api.model
    # def dingtalk_send_message2(self, users, message):
    #     print(222)
    #     config = self.env['sce_dingtalk.config'].search([('res_model_ids', '=', self._name), ('is_master', '=', True)])
    #     print(config)
    #     if config:
    #         config = config[0]
    #         config.send_message(users, message)
    #     else:
    #         print("Cannot find configuration for model:%s" % (self._name,))
    @api.model
    def dingtalk_send_action_card_message(self, users, title, markdown, redirect, target='mobile'):
        # config = self.env['sce_dingtalk.config'].search([('res_model','=',self._name),('is_master','=',True)])
        model = self.env['ir.model'].sudo().search([('model','=',self._name)])
        # print("钉钉")
        # print(users)
        # print(1)
        # print(self._name)  # 传入的模型
        # print(model)
        if model and model.sce_dingtalk_config_id:
            # print(model)
            # print(model.sce_dingtalk_config_id)
            # config = config[0]
            config = model.sce_dingtalk_config_id
            # print(2)
            # print(config)
            url = config.get_linkurl(self._name, redirect, target)
            # print(url)
            # for test, comment in production server
            # if config.test_mode:
            #     users = config.test_user
            config.send_action_card_message(users, title, markdown, url)
        else:
            print("Cannot find configuration for model:%s" % (self._name,))

    @api.model
    def dingtalk_get_user(self, authcode):
        config = self.sudo().env['sce_dingtalk.config'].search([('res_model_ids','=',self._name),('is_master','=',True)])
        if config:
            #print(config) # sce_dingtalk.config(1,)
            config = config[0]
            userid = config.get_userid(authcode)
            # print(userid)
            if userid:
                login = "%s@sce-re.com" % (userid,)
                user = self.sudo().env['res.users'].search([('login','=',login)])
                if not user:
                    userinfo = config.get_userinfo(userid)
                    # Create user.. Specific for SCE
                    if userinfo.get("errmsg")=='ok' and userinfo.get("jobnumber") and userinfo.get("jobnumber").isdigit() and len(userinfo.get("jobnumber"))==6:
                        user = self.sudo().env['res.users'].create({
                            'name': userinfo.get('name'),
                            'login': login,
                        })
                return user
            else:
                print("Cannot find user with authcode.")
        else:
            print("Cannot find configuration for model:%s" % (self._name,))
        return None








#--------------------------------
# 构建告警信息json
#--------------------------------
def messages(user, msg, agentid):
    values = {
        "touser": user,
        "msgtype": 'text',
        "agentid": agentid,
        "text": {'content': msg}
        }
    msges=(bytes(json.dumps(values), 'utf-8'))
    return msges


##############函数结束########################

# corpid = 'wx***********************'
# corpsecret = 'Iwy******************************'
# url = 'https://qyapi.weixin.qq.com'
# msg='test,Python调用企业微信测试'

# #函数调用
# test_token=get_token(url, corpid, corpsecret)
# msg_data= messages(msg)
# send_message(url,test_token, msg_data)
