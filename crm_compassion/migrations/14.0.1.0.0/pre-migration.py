from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_fields(
        env [("recurring.contract", "recurring_contract", "user_id", "ambassador_id")]
    )
