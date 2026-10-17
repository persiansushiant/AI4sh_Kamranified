# ORM table for encrypted key/value persistence. Serialization and encryption belong to the repository.
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .orm_base import OrmBase

class StoredValue(OrmBase):
    __tablename__ = "stored_values"
    # Each configuration key identifies one record and is limited to 200 characters.
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    # Store encrypted JSON text, never a raw password or plain serialized object.
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
