from datetime import datetime
from dateutil import parser
from typing import Optional, Tuple

def parse_date(date_string: str) -> Optional[datetime]:
    """
    Parse a date string in multiple formats and return a datetime object.
    Handles:
    - DD-MMM-YYYY (e.g., 29-Dec-2025)
    - DD/MM/YYYY (e.g., 29/12/2025)
    - YYYY-MM-DD (e.g., 2025-12-29)
    - ISO formats with time (e.g., 2025-12-29T10:30:00Z)
    
    Returns None if parsing fails.
    """
    if not date_string or date_string == "N/A":
        return None
    
    try:
        # Use dateutil parser which handles most formats automatically
        parsed_date = parser.parse(date_string, dayfirst=True)
        return parsed_date
    except (ValueError, TypeError, parser.ParserError):
        # If parsing fails, return None
        return None

def format_date(date_obj: datetime, include_time: bool = True) -> str:
    """
    Format a datetime object to DD/MM/YYYY or DD/MM/YYYY HH:MM format.
    
    Args:
        date_obj: datetime object to format
        include_time: if True and time is not midnight, include HH:MM
    
    Returns:
        Formatted date string
    """
    if not date_obj:
        return "N/A"
    
    # Check if time component is meaningful (not midnight)
    has_time = date_obj.hour != 0 or date_obj.minute != 0
    
    if include_time and has_time:
        return date_obj.strftime("%d/%m/%Y %H:%M")
    else:
        return date_obj.strftime("%d/%m/%Y")

def standardize_date(date_string: str) -> str:
    """
    Parse a date string and standardize it to DD/MM/YYYY or DD/MM/YYYY HH:MM format.
    
    Args:
        date_string: Date string in various formats
    
    Returns:
        Standardized date string in DD/MM/YYYY format (with time if available)
    """
    parsed = parse_date(date_string)
    if parsed:
        return format_date(parsed)
    return "N/A"

def dates_are_equal(date1_str: str, date2_str: str) -> bool:
    """
    Compare two date strings for equality (ignoring time component).
    
    Args:
        date1_str: First date string
        date2_str: Second date string
    
    Returns:
        True if dates are equal (same day), False otherwise
    """
    date1 = parse_date(date1_str)
    date2 = parse_date(date2_str)
    
    # If either date is None, they're not equal
    if date1 is None or date2 is None:
        return False
    
    # Compare only the date part (year, month, day)
    return date1.date() == date2.date()

def calculate_date_difference(date1_str: str, date2_str: str) -> Optional[int]:
    """
    Calculate the difference in days between two dates.
    
    Args:
        date1_str: First date string (earlier date)
        date2_str: Second date string (later date)
    
    Returns:
        Number of days difference (positive if date2 is later, negative if earlier)
        None if parsing fails
    """
    date1 = parse_date(date1_str)
    date2 = parse_date(date2_str)
    
    if date1 is None or date2 is None:
        return None
    
    diff = (date2.date() - date1.date()).days
    return diff

def get_date_range(start_date_str: str, end_date_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Parse two date strings and return them as a tuple of datetime objects.
    Ensures start_date is earlier than end_date (swaps if needed).
    
    Args:
        start_date_str: Start date string
        end_date_str: End date string
    
    Returns:
        Tuple of (start_datetime, end_datetime) or (None, None) if parsing fails
    """
    start = parse_date(start_date_str)
    end = parse_date(end_date_str)
    
    if start is None or end is None:
        return (None, None)
    
    # Ensure start is before end
    if start > end:
        start, end = end, start
    
    return (start, end)

