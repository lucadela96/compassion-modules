# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 Compassion CH (http://www.compassion.ch)
#    Releasing children from poverty in Jesus' name
#    @author: Emanuel Cino <ecino@compassion.ch>
#
#    The licence is in the file __manifest__.py
#
##############################################################################
from odoo import models, api, fields, _
from odoo.tools import safe_eval


class GenerateCommunicationWizard(models.TransientModel):
    _name = 'partner.communication.generate.wizard'

    state = fields.Selection(
        [('edit', 'edit'), ('preview', 'preview')], default='edit'
    )
    selection_domain = fields.Char()
    partner_ids = fields.Many2many(
        'res.partner', string='Recipients',
        default=lambda s: s._default_partners()
    )
    force_language = fields.Selection('_lang_select')
    model_id = fields.Many2one(
        'partner.communication.config', 'Template',
        domain=[('model', '=', 'res.partner')]
    )
    send_mode = fields.Selection('_send_mode_select', default='physical')
    customize_template = fields.Boolean()
    subject = fields.Char()
    body_html = fields.Html()
    report_id = fields.Many2one(
        'ir.actions.report.xml', 'Letter template',
        domain=[('model', '=', 'partner.communication.job')]
    )
    language_added_in_domain = fields.Boolean()
    preview = fields.Html(readonly=True)

    ##########################################################################
    #                             FIELDS METHODS                             #
    ##########################################################################
    @api.model
    def _default_partners(self):
        partners = self.env['res.partner'].browse(self.env.context.get(
            'active_ids', []))
        return partners.ids

    @api.model
    def _lang_select(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    @api.model
    def _send_mode_select(self):
        return self.env['partner.communication.job'].send_mode_select()

    ##########################################################################
    #                             VIEW CALLBACKS                             #
    ##########################################################################
    @api.onchange('selection_domain', 'force_language')
    def onchange_domain(self):
        if self.force_language and not self.language_added_in_domain:
            domain = self.selection_domain or '[]'
            domain = domain[:-1] + ", ('lang', '=', '{}')]".format(
                self.force_language)
            self.selection_domain = domain.replace('[, ', '[')
            self.language_added_in_domain = True
        if self.selection_domain:
            self.partner_ids = self.env['res.partner'].search(
                safe_eval(self.selection_domain))
        if not self.force_language:
            self.language_added_in_domain = False

    @api.onchange('model_id')
    def onchange_model_id(self):
        if self.model_id:
            self.body_html = self.model_id.email_template_id.body_html
            self.subject = self.model_id.email_template_id.subject
            send_mode = self.model_id.send_mode.replace('auto_', '')
            if send_mode in [m[0] for m in self._send_mode_select()]:
                self.send_mode = send_mode

    @api.multi
    def get_preview(self):
        comm_model = 'partner.communication.job'
        config = self.model_id or self.env.ref(
            'partner_communication.default_communication')
        template = config.email_template_id
        model = template.model or comm_model
        res_preview = self.env[comm_model].create({
            'partner_id': self.partner_ids[0].id,
            'config_id': config.id,
            'object_ids': self.env.context.get('object_ids',
                                               self.partner_ids[0].id),
        })
        self.preview = template.render_template(
            self.body_html, model, res_preview.ids)[res_preview.id]
        res_preview.unlink()
        self.state = 'preview'
        return self._reload()

    @api.multi
    def edit(self):
        self.state = 'edit'
        return self._reload()

    def _reload(self):
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'res_model': self._name,
            'target': 'new',
            'context': self.env.context,
        }

    @api.multi
    def generate(self):
        communications = self._get_communications()
        if self.customize_template or not self.model_id:
            default = self.env.ref(
                'partner_communication.default_communication')
            model = self.model_id or default
            template = model.email_template_id.with_context(
                lang=self.force_language or self.env.context.lang)
            new_subjects = template.render_template(
                self.subject, 'partner.communication.job', communications.ids)
            new_texts = template.render_template(
                self.body_html, 'partner.communication.job',
                communications.ids)
            for comm in communications:
                comm.body_html = new_texts[comm.id]
                comm.subject = new_subjects[comm.id]

        return {
            'name': _('Communications'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'view_type': 'form',
            'res_model': 'partner.communication.job',
            'context': self.env.context,
            'domain': [('id', 'in', communications.ids)]
        }

    def _get_communications(self):
        """ Create the communication records """
        comm_obj = self.env['partner.communication.job']
        communications = comm_obj
        default = self.env.ref('partner_communication.default_communication')
        model = self.model_id or default
        for partner in self.partner_ids:
            comm = comm_obj.create({
                'partner_id': partner.id,
                'object_ids': partner.id,
                'config_id': model.id,
                'auto_send': False,
                'send_mode': self.send_mode,
                'report_id': self.report_id.id or model.report_id.id,
            })
            communications += comm
        return communications
