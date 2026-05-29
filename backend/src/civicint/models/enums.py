import enum


class DocumentStatus(str, enum.Enum):
    NEW = "new"
    FETCHED = "fetched"
    EXTRACTED = "extracted"
    TRIAGED = "triaged"
    BUILT = "built"
    ERROR = "error"
    BUDGET_PAUSED = "budget_paused"


class TextStatus(str, enum.Enum):
    PENDING = "pending"
    EXTRACTED = "extracted"
    OCR_DONE = "ocr_done"
    FAILED = "failed"


class CaseStatus(str, enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    UNKNOWN = "unknown"


class Confidence(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"
