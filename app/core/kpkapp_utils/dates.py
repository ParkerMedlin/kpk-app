import datetime as dt

def count_weekend_days(start_date, end_date):
    """Count the number of weekend days between two dates.
    
    Args:
        start_date (datetime.date): Starting date
        end_date (datetime.date): Ending date
        
    Returns:
        int: Total number of Saturdays and Sundays between start_date and end_date
    """

    # Ensure start_date is before end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Initialize counters
    saturday_count = 0
    sunday_count = 0

    # Iterate through each day in the range
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 5:  # Saturday
            saturday_count += 1
        elif current_date.weekday() == 6:  # Sunday
            sunday_count += 1
        current_date += dt.timedelta(days=1)

    return saturday_count + sunday_count

def calculate_production_hours(requireddate):
    """Calculate total available production hours between today and required date.
    
    Args:
        requireddate (datetime.date): Target completion date
        
    Returns:
        int: Total production hours available, excluding weekends (10 hours per workday)
    """

    now = dt.date.today()
    delta = (requireddate - now)
    print(delta)
    # total_hours = 0

    # for i in range(delta + 1):
    #     total_hours += 10

    weekend_days = count_weekend_days(now, requireddate)

    return (delta.days - weekend_days) * 10

def _is_date_string(potential_date):
    """
    Attempts to parse a string into a date using a specific format.
    Returns True if successful, False otherwise.
    """
    try:
        potential_date.strftime('%Y-%m-%d')
        return True
    except Exception as e:
        # ValueError for bad string format, TypeError if it's not a string at all
        return False

