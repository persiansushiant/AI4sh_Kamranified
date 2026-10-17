---
layout: default
title: "Persistence and ORM"
---

# Persistence and ORM


## Configuration Store

```python
from app.services.persistent_store import Store

Store.set("dataset.options", {"separator": ","})
options = Store.get("dataset.options", {})
Store.set_many({"dataset.options": options, "dataset.ready": True})
```

Use stable namespaced keys containing 1–200 characters. Store values must be JSON-serializable; dates need explicit strings. Do not store ORM sessions, files, DataFrames or live model objects. Non-finite numbers are rejected by serialization.

get returns its default only when a record is absent. Saved False, zero, empty string and null retain their meanings. set_many validates and encrypts every value before one transaction. If persistence fails, no success flag should be recorded elsewhere.

## Storage location and encryption

The factory's default database is `instance/workspace.sqlite3`. The repository derives the key using `database_path.with_suffix(".key")`, so the default key is **`instance/workspace.key`**.

StoredValue contains a key primary key and encrypted_value text. JSON is encrypted with Fernet before saving. The adjacent local key enables decryption; this is not an external secret manager or multi-user authorization model. Keep database and key together in private backups. Do not commit either.

## Existing keys

| Key | Meaning |
|---|---|
| database.configuration | database_name, username, password |
| setup.completed | Successfully saved settings |
| workspace.mode | Overall page stage |
| import_data.mode | Import operation stage |
| import.demo_completed | Demo-only transition flag |

ConfigurationSummaryActivity returns its own password to the local masked form. The data route applies Cache-Control: no-store. Other UI views should select only fields they need; never copy credential objects into logs or summaries.

## Structured entities

For real domain data:

1. Define a focused SQLAlchemy model under models/, inheriting OrmBase.
2. Put querying and transactions in a repository under repositories/.
3. Import model modules before metadata.create_all so their tables are known.
4. Return serialized plain values to the activity, not attached ORM objects.
5. Use an explicit schema migration strategy when columns change. create_all creates missing tables; it does not migrate existing columns.
6. Test with temporary databases and keys.

The configuration repository stores local settings independently of the PostgreSQL database named in the form.
