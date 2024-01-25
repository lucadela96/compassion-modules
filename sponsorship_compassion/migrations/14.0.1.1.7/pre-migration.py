import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.add_fields(env, [
        ("invoice_category", "account.move", "account_move", "selection", False, "sponsorship_compassion")
    ])
    env.cr.execute("""
        UPDATE account_move m
        SET invoice_category = i.invoice_category
        FROM account_invoice i
        WHERE m.old_invoice_id = i.id AND i.invoice_category IS NOT NULL;
    """)
