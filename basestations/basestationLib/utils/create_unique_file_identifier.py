import numpy as np
def create_unique_file_identifier(self):
    identifier_parts = []

    if self.operator:
        identifier_parts.append("-".join(self.operator) if isinstance(self.operator, list) else self.operator)
    if self.technology:
        identifier_parts.append("-".join(self.technology) if isinstance(self.technology, list) else self.technology)
    if self.frequency_range:
        if self.frequency_range != [0, np.inf]:
            # Format frequency range with scientific notation or fixed decimals
            freq_str = f"{self.frequency_range[0]:.2f}-{self.frequency_range[1]:.2f}"
            identifier_parts.append(freq_str)
    if self.frequency_band:
        identifier_parts.append("-".join(self.frequency_band) if isinstance(self.frequency_band, list) else self.frequency_band)
    if self.bounding_box:
        # Format bounding box with two decimal places
        bbox_str = "-".join(f"{coord:.2f}" for coord in self.bounding_box)
        identifier_parts.append(bbox_str)
    
    # Date as last section (only date, not time)
    if getattr(self, "date", None) is not None:
        date_str = format_date_only(self.date)
        if date_str:
            identifier_parts.append(date_str)


    # Join parts with underscores
    identifier = "_".join(identifier_parts)

    # Remove any leading/trailing underscores or spaces
    identifier = identifier.strip("_ ").replace(" ", "_")

    return identifier


from datetime import datetime, date, timezone

def format_date_only(value):
    """
    Return an ISO date string 'YYYY-MM-DD' from various date/time types.
    - str: returned as-is (trimmed), assuming already a date-like string
    - datetime: if tz-aware, convert to UTC then take .date(); if naive, take .date()
    - date: convert via .isoformat()
    - pandas.Timestamp / numpy.datetime64: converted if available
    - other: fallback to str(value).strip()
    """
    # Handle None early
    if value is None:
        return None

    # 1) Python datetime.date
    if isinstance(value, date) and not isinstance(value, datetime):
        return value.isoformat()  # YYYY-MM-DD

    # 2) Python datetime.datetime
    if isinstance(value, datetime):
        # If tz-aware, convert to UTC before extracting date
        if value.tzinfo is not None and value.tzinfo.utcoffset(value) is not None:
            value = value.astimezone(timezone.utc)
        # Extract date component only
        return value.date().isoformat()

    # 3) pandas.Timestamp (optional)
    try:
        import pandas as pd  # will work only if pandas is installed
        if isinstance(value, pd.Timestamp):
            # If tz-aware, convert to UTC
            if value.tz is not None:
                value = value.tz_convert("UTC")
            return value.date().isoformat()
    except Exception:
        pass

    # 4) numpy.datetime64 (optional)
    try:
        import numpy as np
        if isinstance(value, np.datetime64):
            # Convert to python datetime (assumes UTC if time component exists)
            dt = np.datetime_as_string(value, unit='D')  # trims to date component directly
            return dt  # already YYYY-MM-DD
    except Exception:
        pass

    # 5) str inputs: use as-is, trimmed
    if isinstance(value, str):
        s = value.strip()
        # If you want to enforce YYYY-MM-DD, you could parse and reformat here.
        return s

    # 6) Fallback: string representation trimmed
    return str(value).strip()
