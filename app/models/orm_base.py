# Shared SQLAlchemy declarative base. ORM models must inherit this same base to share metadata.
from sqlalchemy.orm import DeclarativeBase

# All mapped subclasses contribute tables to this base metadata.
# create_all creates missing tables, but does not migrate existing table columns.
class OrmBase(DeclarativeBase):
    pass
