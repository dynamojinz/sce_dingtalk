# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ModelConfig(models.Model):
    _inherit='ir.model'

    sce_dingtalk_config_id = fields.Many2one('sce_dingtalk.config')
    

