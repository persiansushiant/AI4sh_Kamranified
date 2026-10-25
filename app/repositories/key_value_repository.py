# SQLite repository for JSON-serializable configuration values encrypted with Fernet.
# The adjacent key file is required for decryption; back up the database and key together.
import json
import threading
from pathlib import Path
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import sessionmaker
from ..models.orm_base import OrmBase
from ..models.stored_value import StoredValue

class KeyValueRepository:
    # Prepare the local SQLite database, encryption key, session factory, and write lock.
    def __init__(self, database_path):
        database_path = Path(database_path).resolve()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        # Derive the key filename from the database path; keep both files together.
        key_path = database_path.with_suffix(".key")
        try:
            # Exclusive creation avoids overwriting an existing encryption key.
            with key_path.open("xb") as file:
                file.write(Fernet.generate_key())
            # Request owner-only filesystem permissions for the newly created key.
            key_path.chmod(0o600)
        except FileExistsError:
            pass
        self.cipher = Fernet(key_path.read_bytes())
        self.engine = create_engine("sqlite:///" + str(database_path), connect_args={"timeout": 30})
        self.sessions = sessionmaker(bind=self.engine)
        # Serialize writes through this repository instance; this is not a cross-process lock.
        self.lock = threading.RLock()
        # Imported ORM modules must already be registered with this metadata.
        OrmBase.metadata.create_all(self.engine)

    # Validate the key, fetch a record, then decrypt and decode its JSON value.
    # The default is returned only when no record exists; stored null/false/zero remain intact.
    def get(self, key, default=None):
        self.validate_key(key)
        with self.sessions() as session:
            row = session.get(StoredValue, key)
            if row is None:
                return default
            return json.loads(self.cipher.decrypt(row.encrypted_value.encode()).decode())

    # Delegate a single value to the same transactional path used for batch writes.
    def set(self, key, value):
        self.set_many({key: value})

    # Validate and encrypt every value before opening the write transaction.
    # The session commits all records together or rolls back on failure.
    def set_many(self, values):
        encoded = {}
        for key, value in values.items():
            self.validate_key(key)
            # Reject non-finite numbers and serialize Unicode before encrypting the value.
            serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
            encoded[key] = self.cipher.encrypt(serialized.encode()).decode()
        # Open one transaction for all prepared records; exceptions trigger rollback.
        with self.lock, self.sessions.begin() as session:
            for key, value in encoded.items():
                statement = insert(StoredValue).values(key=key, encrypted_value=value)
                session.execute(statement.on_conflict_do_update(
                    index_elements=[StoredValue.key],
                    set_={"encrypted_value": statement.excluded.encrypted_value},
                ))

    @staticmethod
    # Reject blank, non-string, and oversized keys; accepted keys are not trimmed.
    def validate_key(key):
        if not isinstance(key, str) or not key.strip() or len(key) > 200:
            raise ValueError("Store key must contain 1–200 characters")
