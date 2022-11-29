from datetime import datetime
from pony.orm import *
from database.db import db


class Project(db.Entity):
    name = PrimaryKey(str)

    api_key = Required(str)
    api_token_count = Required(int, size=64)
    used_api_tokens = Optional(int, size=64, sql_default=0)
    archive_mode = Optional(bool, sql_default=False)

    activated = Optional(bool, sql_default=False)
    payments = Set(lambda: Payment, reverse='project')

    active = Required(bool, sql_default=False)
    user_cancelled = Optional(bool, sql_default=False)
    xquery = Required(bool, sql_default=True)
    hydra = Required(bool, sql_default=False)


class Payment(db.Entity):
    pending = Optional(bool) # Set to True for 1 hr after create_project or extend_project called, then False again
    eth_token = Optional(str)
    eth_address = Optional(str)
    eth_privkey = Optional(str)
    avax_token = Optional(str)
    avax_address = Optional(str)
    avax_privkey = Optional(str)
    nevm_token = Optional(str)
    nevm_address = Optional(str)
    nevm_privkey = Optional(str)

    min_amount_usd = Optional(float)
    min_amount_ablock_usd = Optional(float)
    min_amount_aablock_usd = Optional(float)
    min_amount_sysblock_usd = Optional(float)

    min_amount_eth = Optional(float)
    min_amount_ablock = Optional(float)
    min_amount_avax = Optional(float)
    min_amount_aablock = Optional(float)
    min_amount_sys = Optional(float)
    min_amount_sysblock = Optional(float)

    tx_hash = Optional(str)
    amount_eth = Optional(float)
    amount_ablock = Optional(float)
    amount_avax = Optional(float)
    amount_aablock = Optional(float)
    amount_sys = Optional(float)
    amount_sysblock = Optional(float)
    quote_start_time = Required(datetime)

    project = Required(Project, reverse='payments')


db.generate_mapping(create_tables=True)
