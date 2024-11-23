from datetime import datetime
from frontend.translations import get_browser_language


def format_number(value: float, decimal_places: int = 2) -> str:
    """Format number according to current language"""
    lang = get_browser_language()

    # Format the number with specified decimal places
    formatted = f"{value:.{decimal_places}f}"

    # Split into whole and decimal parts
    parts = formatted.split('.')
    whole = parts[0]
    decimal = parts[1] if len(parts) > 1 else ''

    # Add thousand separators
    if lang == 'nl':
        # Dutch format: 1.234,56
        whole = '.'.join(whole[i:i + 3]
                         for i in range(0, len(whole), 3)).strip('.')
        return f"{whole},{decimal}" if decimal else whole
    else:
        # English format: 1,234.56
        whole = ','.join(whole[i:i + 3]
                         for i in range(0, len(whole), 3)).strip(',')
        return f"{whole}.{decimal}" if decimal else whole


def format_currency(value: float, decimal_places: int = 2) -> str:
    """Format currency value according to current language"""
    lang = get_browser_language()
    formatted_number = format_number(value, decimal_places)

    if lang == 'nl':
        return f"€ {formatted_number}"
    else:
        return f"€{formatted_number}"


def format_date(date: datetime, include_time: bool = False) -> str:
    """Format date according to current language"""
    lang = get_browser_language()

    # Define month names for both languages
    months_nl = [
        'januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli',
        'augustus', 'september', 'oktober', 'november', 'december'
    ]
    months_en = [
        'January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August', 'September', 'October', 'November', 'December'
    ]

    if lang == 'nl':
        # Dutch format: 31 december 2024
        date_str = f"{date.day} {months_nl[date.month-1]} {date.year}"
        if include_time:
            date_str += f" {date.hour:02d}:{date.minute:02d}:{date.second:02d}"
    else:
        # English format: December 31, 2024
        date_str = f"{months_en[date.month-1]} {date.day}, {date.year}"
        if include_time:
            # 12-hour format for English
            hour = date.hour % 12
            if hour == 0:
                hour = 12
            am_pm = "PM" if date.hour >= 12 else "AM"
            date_str += f" {hour}:{date.minute:02d}:{date.second:02d} {am_pm}"

    return date_str


def format_percentage(value: float, decimal_places: int = 1) -> str:
    """Format percentage according to current language"""
    formatted_number = format_number(value, decimal_places)
    return f"{formatted_number}%"
