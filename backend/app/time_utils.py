"""统一的 HTTP 时间解析和上海本地统计边界。"""

from datetime import UTC, date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import AfterValidator

SHANGHAI = ZoneInfo("Asia/Shanghai")


def require_aware_datetime(value: datetime) -> datetime:
    """拒绝没有偏移的时间，并统一转换成 UTC。"""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("时间必须包含 Z 或 UTC 偏移")
    return value.astimezone(UTC)


AwareDateTime = Annotated[datetime, AfterValidator(require_aware_datetime)]


def stored_datetime_as_utc(value: datetime) -> datetime:
    """把 SQLite 返回的无时区值按数据库 UTC 约定恢复为 aware datetime。"""

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_query_datetime(value: str | None, *, name: str) -> datetime | None:
    """严格解析查询参数中的 RFC 3339 时间。"""

    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{name} 必须是带 Z 或 UTC 偏移的 ISO 8601 时间") from error
    try:
        return require_aware_datetime(parsed)
    except ValueError as error:
        raise ValueError(f"{name} 必须包含 Z 或 UTC 偏移") from error


def month_bounds(today: date | None = None) -> tuple[datetime, datetime]:
    """返回上海本地当前自然月的 UTC 左闭右开边界。"""

    local = today or datetime.now(SHANGHAI).date()
    start = datetime.combine(local.replace(day=1), time.min, SHANGHAI)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)
    return start.astimezone(UTC), next_month.astimezone(UTC)


def date_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    """把上海本地日期范围转换成 UTC 左闭右开边界。"""

    if start_date >= end_date:
        raise ValueError("startDate 必须早于 endDate")
    start = datetime.combine(start_date, time.min, SHANGHAI)
    end = datetime.combine(end_date, time.min, SHANGHAI)
    return start.astimezone(UTC), end.astimezone(UTC)


def previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """返回与当前期间等长且紧邻其前的期间。"""

    duration = end - start
    return start - duration, start


def bucket_start(value: datetime, granularity: str) -> datetime:
    """按上海本地时间计算日、周、月时间桶起点。"""

    local = value.astimezone(SHANGHAI)
    if granularity == "day":
        start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    elif granularity == "week":
        start = (local - timedelta(days=local.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        start = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(UTC)


def add_bucket(value: datetime, granularity: str) -> datetime:
    """返回下一个连续时间桶起点。"""

    local = value.astimezone(SHANGHAI)
    if granularity == "day":
        next_local = local + timedelta(days=1)
    elif granularity == "week":
        next_local = local + timedelta(days=7)
    else:
        if local.month == 12:
            next_local = local.replace(year=local.year + 1, month=1)
        else:
            next_local = local.replace(month=local.month + 1)
    return next_local.astimezone(UTC)


__all__ = (
    "SHANGHAI",
    "AwareDateTime",
    "add_bucket",
    "bucket_start",
    "date_bounds",
    "month_bounds",
    "parse_query_datetime",
    "previous_period",
    "require_aware_datetime",
    "stored_datetime_as_utc",
)
