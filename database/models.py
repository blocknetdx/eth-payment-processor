from datetime import datetime
from pony.orm import *
from database.db import db


class Project(db.Entity):
    name = PrimaryKey(str)

    api_key = Required(str)
    api_token_count = Required(int, size=64)
    used_api_tokens = Optional(int, size=64, sql_default=0)
    archive_mode = Optional(bool, sql_default=False)

    expires = Optional(datetime)
    payments = Set(lambda: Payment, reverse='project')

    active = Required(bool, sql_default=False)
    user_cancelled = Required(bool, sql_default=False)


class Payment(db.Entity):
    pending = Optional(bool)
    eth_token = Optional(str)
    eth_address = Optional(str)
    eth_privkey = Optional(str)
    avax_token = Optional(str)
    avax_address = Optional(str)
    avax_privkey = Optional(str)
    nevm_token = Optional(str)
    nevm_address = Optional(str)
    nevm_privkey = Optional(str)

    tier1_expected_amount_eth = Optional(float)
    tier2_expected_amount_eth = Optional(float)
    tier1_expected_amount_ablock = Optional(float)
    tier2_expected_amount_ablock = Optional(float)
    tier1_expected_amount_aablock = Optional(float)
    tier2_expected_amount_aablock = Optional(float)
    tier1_expected_amount_sysblock = Optional(float)
    tier2_expected_amount_sysblock = Optional(float)
    tier1_expected_amount_wsys = Optional(float)
    tier2_expected_amount_wsys = Optional(float)

    tx_hash = Optional(str)
    amount_eth = Optional(float)
    amount_ablock = Optional(float)
    amount_aablock = Optional(float)
    amount_sysblock = Optional(float)
    amount_wsys = Optional(float)
    start_time = Required(datetime)

    project = Required(Project, reverse='payments')


db.generate_mapping(create_tables=True)
