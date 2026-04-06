import logging
from datetime import date, datetime, time, timezone

from dateutil import parser


def parse_utc_datetime(value: str) -> datetime:
    try:
        return parser.parse(value)
    except Exception as e:
        logging.error(f"Error parsing datetime {value}: {e}")
        raise ValueError(f"Unsupported date format: {value}")


def max_day_daterange(start_date: str, end_date: str) -> tuple[datetime, datetime]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end, time.max)
    return start_dt, end_dt


def datetime_to_string(value: datetime) -> str:
    return value.strftime("%d-%m-%Y %H:%M:%S")


def _parse_date(value: str) -> date:
    cleaned = extract_date_part(value)
    try:
        return parser.parse(cleaned)
    except Exception as e:
        logging.error(f"Error parsing date: {e}")
        raise ValueError(f"Unsupported date format: {value}")


def extract_date_part(value: str) -> str:
    cleaned = value.strip()
    if " " in cleaned:
        cleaned = cleaned.split(" ", 1)[0]
    if "T" in cleaned:
        cleaned = cleaned.split("T", 1)[0]
    if len(cleaned) > 10 and cleaned[10] in ("+", "-"):
        cleaned = cleaned[:10]
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1]
    return cleaned
