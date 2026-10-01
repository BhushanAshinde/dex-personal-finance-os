from .database import engine, Base, SessionLocal
from .models import *
DEFAULTS=["Food","Groceries","Travel","Fuel","Shopping","Bills","Entertainment","Health","Other"]
Base.metadata.create_all(engine)
db=SessionLocal()
try:
    for name in DEFAULTS:
        if not db.query(Category).filter_by(name=name).first(): db.add(Category(name=name))
    db.commit()
finally: db.close()
