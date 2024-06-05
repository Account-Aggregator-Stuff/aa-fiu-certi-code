from datetime import datetime, timedelta

import pytz


def validate_given_time(given_time_str, time_range_check_in_min=15):
    try:
        # Parse the given time string into a datetime object
        given_time = datetime.strptime(given_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")

        # Get the current time
        current_time = datetime.utcnow()  # Use utcnow() to handle the "Z" (Zulu time) in the input format

        # Define the time range
        time_range = timedelta(minutes=time_range_check_in_min)

        # Calculate the lower and upper bounds
        lower_bound = current_time - time_range
        upper_bound = current_time + time_range

        # Check if the given time is within the valid range
        if lower_bound <= given_time <= upper_bound:
            return True
        else:
            print ("Given time is not within the valid range")
            return False
    except:
        return False


def create_timestamp():
    return datetime.utcnow().replace(tzinfo=pytz.utc).strftime("%Y-%m-%dT%H:%M:%S.00Z")