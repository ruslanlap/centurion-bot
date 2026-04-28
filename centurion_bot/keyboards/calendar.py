import calendar
from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CALLBACK_PREFIX = "cal"
IGNORE = f"{CALLBACK_PREFIX}:ignore"
PREV = f"{CALLBACK_PREFIX}:prev"
NEXT = f"{CALLBACK_PREFIX}:next"
NO_DATE = f"{CALLBACK_PREFIX}:nodate"


def _day_cb(year: int, month: int, day: int) -> str:
    return f"{CALLBACK_PREFIX}:day:{year}:{month}:{day}"


def create_calendar(year: int | None = None, month: int | None = None) -> InlineKeyboardMarkup:
    today = date.today()
    year = year or today.year
    month = month or today.month

    row_header = [InlineKeyboardButton(text=f"{calendar.month_name[month]} {year}", callback_data=IGNORE)]

    row_weekdays = [
        InlineKeyboardButton(text=d, callback_data=IGNORE) for d in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    ]

    cal = calendar.monthcalendar(year, month)
    rows: list[list[InlineKeyboardButton]] = []
    for week in cal:
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=IGNORE))
            else:
                label = f"*{day_num}*" if date(year, month, day_num) == today else str(day_num)
                row.append(InlineKeyboardButton(text=label, callback_data=_day_cb(year, month, day_num)))
        rows.append(row)

    prev_month = date(year, month, 1) - timedelta(days=1)
    next_month = date(year, month, 28) + timedelta(days=4)
    row_nav = [
        InlineKeyboardButton(text="<", callback_data=f"{PREV}:{prev_month.year}:{prev_month.month}"),
        InlineKeyboardButton(text="No date", callback_data=NO_DATE),
        InlineKeyboardButton(text=">", callback_data=f"{NEXT}:{next_month.year}:{next_month.month}"),
    ]

    keyboard = [row_header, row_weekdays, *rows, row_nav]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def parse_calendar_callback(data: str) -> tuple[bool, date | None, bool]:
    """Returns (handled, selected_date, show_new_calendar).

    - handled=True means we recognised the prefix.
    - selected_date is set only when a day was picked.
    - show_new_calendar=True when prev/next month was pressed (re-render needed).
    """
    parts = data.split(":")
    if parts[0] != CALLBACK_PREFIX:
        return False, None, False

    action = parts[1]
    if action == "day":
        return True, date(int(parts[2]), int(parts[3]), int(parts[4])), False
    if action == "nodate":
        return True, None, False
    if action in ("prev", "next"):
        return True, None, True
    return True, None, False
