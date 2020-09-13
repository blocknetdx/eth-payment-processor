from datetime import datetime

from pony.orm import *
from database.db import db


class Project(db.Entity):
    name = PrimaryKey(str)
    paymenthash = Required(str)
    allocatedapicalls = Required(int)
    usedapicalls = Required(int)

    expires = Required(datetime)
    payments = Set(lambda: Payment, reverse='pending')

    active = Required(bool)


class Payment(db.Entity):
    pending = Required(bool)
    address = Required(str)
    amount = Optional(float)

    start_time = Required(datetime)

    project = Required(Project)


db.generate_mapping(create_tables=True)
