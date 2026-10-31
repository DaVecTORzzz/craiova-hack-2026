from datetime import timezone
from sqlmodel.sql.sqltypes import UTCDateTime

# Compatibility shim for SQLModel 0.0.48+ UTCDateTime to support naive UTC datetimes
# as required by Section 1 ("Store datetimes as naive UTC in the DB") and Section 4.
_orig_bind = UTCDateTime.process_bind_param
_orig_result = UTCDateTime.process_result_value


def _patched_bind(self, value, dialect):
    if value is not None and value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return _orig_bind(self, value, dialect)


def _patched_result(self, value, dialect):
    res = _orig_result(self, value, dialect)
    if res is not None:
        return res.replace(tzinfo=None)
    return res


UTCDateTime.process_bind_param = _patched_bind
UTCDateTime.process_result_value = _patched_result
