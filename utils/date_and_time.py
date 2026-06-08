from datetime import datetime
import holidays

def get_today_info():
    """Get today's date and time information"""
    today = datetime.now()
    
    # Get month
    month = today.month
    
    # Check if it's a weekend (Saturday=5, Sunday=6)
    is_weekend = int(today.weekday() >= 5)
    
    # Check if it's a holiday (India holidays)
    india_holidays = holidays.India()
    is_holiday = int(today.date() in india_holidays)
    
    # Get hour and minute
    hour = today.hour
    minute = today.minute
    
    # Round minute to 0, 15, 30, or 45
    if minute < 8:
        minute = 0
    elif minute < 23:
        minute = 15
    elif minute < 38:
        minute = 30
    elif minute < 53:
        minute = 45
    else:
        minute = 0
    
    return {
        'month': month,
        'holiday': is_holiday,
        'is_weekend': is_weekend,
        'hour': hour,
        'minute': minute
    }

# Usage
info = get_today_info()
print(info)