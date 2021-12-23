from datetime import datetime
from pony.orm import *
from database.db import db


class Project(db.Entity):
    name = PrimaryKey(str)

    api_key = Required(str)
    api_token_count = Required(int)
    used_api_tokens = Optional(int, sql_default=0)
    archive_mode = Optional(bool, sql_default=False)

    expires = Optional(datetime)
    payments = Set(lambda: Payment, reverse='project')

    active = Required(bool, sql_default=False)


class Payment(db.Entity):
    pending = Optional(bool)
    eth_address = Optional(str)
    avax_address = Optional(str)

    tier1_expected_amount = Optional(float)
    tier2_expected_amount = Optional(float)
    tier1_expected_amount_ablock = Optional(float)
    tier2_expected_amount_ablock = Optional(float)
    tier1_expected_amount_aablock = Optional(float)
    tier2_expected_amount_aablock = Optional(float)

    tx_hash = Optional(str)
    amount = Optional(float)
    amount_ablock = Optional(float)
    amount_aablock = Optional(float)
    start_time = Required(datetime)

    project = Required(Project, reverse='payments')


db.generate_mapping(create_tables=True)
