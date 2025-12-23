from datetime import datetime
from typing import List, Dict

# French Public Holidays 2025-2026
FRENCH_HOLIDAYS = {
    # 2025
    "2025-01-01": "New Year's Day",
    "2025-04-21": "Easter Monday",
    "2025-05-01": "Labour Day",
    "2025-05-08": "Victory Day",
    "2025-05-29": "Ascension Day",
    "2025-06-09": "Whit Monday",
    "2025-07-14": "Bastille Day",
    "2025-08-15": "Assumption Day",
    "2025-11-01": "All Saints' Day",
    "2025-11-11": "Armistice Day",
    "2025-12-25": "Christmas Day",
    
    # 2026
    "2026-01-01": "New Year's Day",
    "2026-04-06": "Easter Monday",
    "2026-05-01": "Labour Day",
    "2026-05-08": "Victory Day",
    "2026-05-14": "Ascension Day",
    "2026-05-25": "Whit Monday",
    "2026-07-14": "Bastille Day",
    "2026-08-15": "Assumption Day",
    "2026-11-01": "All Saints' Day",
    "2026-11-11": "Armistice Day",
    "2026-12-25": "Christmas Day",
}

# India Public Holidays 2025-2026 (National Holidays)
INDIA_HOLIDAYS = {
    # 2025
    "2025-01-26": "Republic Day",
    "2025-03-14": "Holi",
    "2025-03-31": "Eid ul-Fitr",
    "2025-04-10": "Mahavir Jayanti",
    "2025-04-14": "Ambedkar Jayanti",
    "2025-04-18": "Good Friday",
    "2025-05-01": "May Day",
    "2025-06-07": "Eid ul-Adha",
    "2025-07-06": "Muharram",
    "2025-08-15": "Independence Day",
    "2025-08-27": "Janmashtami",
    "2025-09-05": "Milad un-Nabi",
    "2025-10-02": "Gandhi Jayanti",
    "2025-10-21": "Dussehra",
    "2025-10-22": "Diwali",
    "2025-11-05": "Guru Nanak Jayanti",
    "2025-12-25": "Christmas Day",
    
    # 2026
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-20": "Eid ul-Fitr",
    "2026-03-30": "Mahavir Jayanti",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Ambedkar Jayanti",
    "2026-05-01": "May Day",
    "2026-05-28": "Eid ul-Adha",
    "2026-06-25": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-08-16": "Janmashtami",
    "2026-08-25": "Milad un-Nabi",
    "2026-10-02": "Gandhi Jayanti",
    "2026-10-10": "Dussehra",
    "2026-10-29": "Diwali",
    "2026-11-24": "Guru Nanak Jayanti",
    "2026-12-25": "Christmas Day",
}

def get_holidays_between_dates(start_date: datetime, end_date: datetime) -> Dict[str, List[str]]:
    """
    Get all French and India holidays between two dates.
    
    Args:
        start_date: Start date (datetime object)
        end_date: End date (datetime object)
    
    Returns:
        Dictionary with 'french' and 'india' keys containing lists of holiday strings
    """
    if start_date is None or end_date is None:
        return {"french": [], "india": []}
    
    # Ensure start is before end
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    french_holidays = []
    india_holidays = []
    
    # Check French holidays
    for date_str, holiday_name in FRENCH_HOLIDAYS.items():
        holiday_date = datetime.strptime(date_str, "%Y-%m-%d")
        if start_date.date() <= holiday_date.date() <= end_date.date():
            french_holidays.append(f"{holiday_name} ({holiday_date.strftime('%d/%m/%Y')})")
    
    # Check India holidays
    for date_str, holiday_name in INDIA_HOLIDAYS.items():
        holiday_date = datetime.strptime(date_str, "%Y-%m-%d")
        if start_date.date() <= holiday_date.date() <= end_date.date():
            india_holidays.append(f"{holiday_name} ({holiday_date.strftime('%d/%m/%Y')})")
    
    return {
        "french": french_holidays,
        "india": india_holidays
    }

def format_holidays_for_summary(holidays: Dict[str, List[str]]) -> str:
    """
    Format holiday information for inclusion in AI summary.
    
    Args:
        holidays: Dictionary with 'french' and 'india' keys containing lists of holidays
    
    Returns:
        Formatted string for AI prompt
    """
    if not holidays["french"] and not holidays["india"]:
        return "No public holidays between the dates."
    
    result = []
    
    if holidays["french"]:
        result.append("French Holidays: " + ", ".join(holidays["french"]))
    
    if holidays["india"]:
        result.append("India Holidays: " + ", ".join(holidays["india"]))
    
    return "; ".join(result)

