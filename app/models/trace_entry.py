# Trace enums and immutable entry data. These definitions are not persistent ORM tables.
from dataclasses import dataclass, asdict
from enum import Enum

# Allowed trace categories, shared by validation and UI filter choices.
class TraceSection(str, Enum):
    JOB = "job"
    SCHEME = "scheme"
    PILOT = "pilot"
    PROCESS = "process"
    DISPATCHER = "dispatcher"
    SQL = "sql"
    EXCEL = "excel"
    ML = "ml"

# Allowed presentation statuses; these do not control job execution.
class TraceStatus(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

# Prevent reassignment of entry fields after construction.
@dataclass(frozen=True)
class TraceEntry:
    id: int
    # Timestamp text is supplied by the runtime; this model does not generate it.
    time: str
    section: TraceSection
    status: TraceStatus
    message: str

    def to_dict(self):
        data = asdict(self)
        # Convert enum fields to their public string values for browser serialization.
        data["section"] = self.section.value
        data["status"] = self.status.value
        return data
