from datetime import datetime, timedelta

def to_seconds(time):
    """Takes a formatted time and converts it to seconds

    Args:
    time -- a string formatted as HH:MM:SS

    Returns:
    Time as a span of seconds
    """
    t = None
    try:
        t = datetime.strptime(time, "%H:%M:%S")
    except ValueError:
        t = datetime.strptime(time, "%M:%S")
    td = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)
    return td.total_seconds()