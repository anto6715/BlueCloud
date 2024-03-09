import calendar
import dateutil.parser as parser
import dateutil.relativedelta as relativedelta
import datetime
import re
from dateutil.tz import tzutc


def add_years(orig_date, x):
    """
        This function increase the date pass as argument by x years
        @param orig_date: datetime object, the date to be increment
        @param x: number of years to add to orig_date
        @return: returns the original date to which they were added x years
    """
    return add_months(orig_date, x * 12)


def add_months(orig_date, x):
    """
    This function increase the date pass as argument by x months
    @param orig_date: datetime object, the date to be increment
    @param x: number of months to add to orig_date
    @return: returns the original date to which they were added x months
    """
    # advance year and month by one month
    new_year = orig_date.year
    new_month = orig_date.month + x
    # note: in datetime.date, months go from 1 to 12
    while new_month > 12:
        new_year += 1
        new_month -= 12

    last_day_of_month = calendar.monthrange(new_year, new_month)[1]
    new_day = min(orig_date.day, last_day_of_month)

    return orig_date.replace(year=new_year, month=new_month, day=new_day)


def get_years(start_time, end_time):
    """
    This function get all the years contained in the time range start_range/end_range
    @param start_time: datatime object, the start of rime range
    @param end_time: datatime object, the end of rime range
    @return: A list of years
    """
    year_range = list()
    for year in range(start_time.year, end_time.year + 1):
        year_range.append(year)
    return year_range


def print_month_range(start_time, end_time, year, time_patterns):
    """
    Given a time range, this function prints the pattern yearMM for each MM contained in the time range
    @param start_time: datatime object, the start of rime range
    @param end_time: datatime object, the end of rime range
    @param year: Value of the year
    @return: A list of pattern yearMM where MM are the month of the year in
    the time range start_time/end_time
    """
    if start_time.year == year:
        start = start_time
    else:
        start = datetime.datetime(year=year, month=1, day=1)
    if end_time.year == year:
        end = end_time
    else:
        end = datetime.datetime(year=year, month=12, day=1)
    while start <= end:
        time_patterns.append(start.strftime("%Y%m"))
        start = add_months(start, 1)


def get_years_by_month(start_time, end_time, month, time_patterns: list):
    """
    This function returns a list of years in the time range start_time/end_time
    with the fixed month passed as argument
    @param month: a specific month
    @param start_time: datatime object, the start of rime range
    @param end_time: datatime object, the end of rime range
    @return: list of patter YYYYmonth
    """
    print(type(start_time.month))
    if start_time.month <= month:
        start = datetime.datetime(year=start_time.year, month=month, day=1)
    else:
        start = datetime.datetime(year=start_time.year + 1, month=month, day=1)
    if end_time.month >= month:
        end = datetime.datetime(year=end_time.year, month=month, day=1)
    else:
        end = datetime.datetime(year=end_time.year - 1, month=month, day=1)
    while start <= end:
        # print(str(start.year) + str(start.month).zfill(2))
        time_patterns.append(start.strftime("%Y%m"))
        start = add_months(start, 12)


def get_date_pattern(start_time, end_time, month=None):
    """
    This function compute a list of time patter equals to "YYYY" if an year
    is complete included into the time range start_time/end_time, else
    the pattern will be "YYYYMM" with MM the month of YYYY years contained
    in the time range
    @param month: a specific month - optional
    @param start_time: datatime object, the start of rime range
    @param end_time: datatime object, the end of rime range
    @return: A list of pattern ( YYYY or YYYYMM )
    """
    time_patterns = list()
    if month is not None:
        get_years_by_month(start_time, end_time, month, time_patterns)
        return time_patterns
    else:
        years = get_years(start_time, end_time)
        if start_time.month == 1 and end_time.month == 12:
            for year in years:
                time_patterns.append(str(year))
        else:
            for year in years:
                if is_year_complete(start_time, end_time, year):
                    time_patterns.append(str(year))
                else:
                    print_month_range(start_time, end_time, year, time_patterns)
        return time_patterns


def is_year_complete(start_time, end_time, year):
    """
    This function checks if years is completely contained in a time range
    @param start_time: datatime object, the start of rime range
    @param end_time: datatime object, the end of rime range
    @param year: Value of year to be checked
    @return: True if year is completely contained in the time range start_time/end_time
    """
    start_year = datetime.datetime(year=year, month=1, day=1)
    end_year = datetime.datetime(year=year, month=12, day=1)
    if start_time <= start_year and end_year <= end_time:
        return True
    else:
        return False


def get_tCounterTotal(td, RefTimeUnits):
    """
    This functions converts a timedelta object into hours or minutes in according to RefTimeUnits
    @param td: timedelta object
    @param RefTimeUnits: string with netCDF time reference
    @return: the timedelta expressed in hours or minutes
    """
    if 'minute' in RefTimeUnits:
        x = 60
    elif 'hour' in RefTimeUnits:
        x = 3600
    else:
        raise Exception("Unknown netCDF reference Time")
    return (td.seconds + td.days * 24 * 3600) / x


def extract_date_from_text(text):
    """
    @param text: A text string that contains a date
    @return:
    """
    match_date = re.search(r'\d{4}-\d{2}-\d{2}', text)
    if match_date is None:
        match_date = re.search(r'\d{2}-\d{2}-\d{4}', text)

    if match_date is None:
        raise Exception("Can't find date in: ", text)

    match_time = re.search(r'\d{2}:\d{2}:\d{2}', text)

    str_date = match_date.group() + ' ' + match_time.group()
    return parser.parse(str_date)


def get_date_from_timedelta(td, RefTimeUnits):
    """
    This functions converts a timedelta object into hours or minutes in according to RefTimeUnits
    @param td: timedelta object
    @param RefTimeUnits: string with netCDF time reference
    @return: the timedelta expressed in hours or minutes
    """
    if 'hour' in RefTimeUnits:
        delta = datetime.timedelta(hours=int(td))
    elif 'minute' in RefTimeUnits:
        delta = datetime.timedelta(minutes=int(td))
    elif 'second' in RefTimeUnits:
        delta = datetime.timedelta(seconds=int(td))
    else:
        raise Exception("Unknown netCDF reference Time")
    refDate = extract_date_from_text(RefTimeUnits)

    return refDate + delta


def string_to_iso_date(date, default_month=None, default_day=None, default_hours=None):
    """
    This function read a date as string and return it in ISO format.
    Only year in strin date in mandatory, the others parameters are set to a defualt
    value if missing.
    It's possible to set the default value for month, day and hours
    @param date: A date in string format
    @param default_month: A value to set if month is not present on date
    @param default_day: A value to set if day is not present on date
    @param default_hours: A value to set if  hours is not present on date
    @return: date in ISO format: YYYY-MM-ddThh:mm:ss
    """
    YYYY = 1
    MM = default_month if default_month is not None else 1
    dd = default_day if default_day is not None else 1
    hh = default_hours if default_hours is not None else 0
    mm = 0
    ss = 0

    return parser.parse(date, default=datetime.datetime(YYYY, MM, dd, hh, mm, ss))


def get_years_number(start_date, end_date):
    start_date = string_to_iso_date(start_date)
    end_date = string_to_iso_date(end_date)
    return end_date.year - start_date.year + 1  # end date is included


def get_months_number(start_date, end_date):
    start_date = string_to_iso_date(start_date)
    end_date = string_to_iso_date(end_date)
    nyears = relativedelta.relativedelta(end_date, start_date).years
    nmonths = relativedelta.relativedelta(end_date, start_date).months + 1
    return nyears * 12 + nmonths


def get_iso_timestamp():
    time = datetime.datetime.now(tz=tzutc()).replace(microsecond=0).isoformat()
    return time


def get_utc_monthly_range(start_time, end_time, month=None):
    """
    Given a time range, this function prints the pattern yearMM for each MM contained in the time range
    @param start_time: datatime object, the start of rime range
    @param end_time: datatime object, the end of rime range
    @param month: value of the month
    @return: A list of pattern yearMM where MM are the month of the year in
    the time range start_time/end_time
    """
    start = datetime.datetime(year=start_time.year, month=start_time.month, day=1)
    end = datetime.datetime(year=end_time.year, month=end_time.month, day=1)
    time_patterns = list()
    while start <= end:
        if month is not None and start.month != month:
            start = add_months(start, 1)
            continue

        month_range = get_month_range(date=start)
        time_patterns.append(month_range)
        start = add_months(start, 1)
    return time_patterns


def get_month_range(date: datetime = None, YYYYMM: str = None):
    month_range = list()
    if YYYYMM is not None:
        date = datetime.datetime(year=int(YYYYMM[0:4]), month=int(YYYYMM[4:6]), day=1)
    last_month_day = calendar.monthrange(date.year, date.month)[1]
    date_end_month = datetime.datetime(year=date.year, month=date.month, day=last_month_day)
    month_range.append(date.strftime("%Y-%m-%d") + 'T00:00:00.000Z')
    month_range.append(date_end_month.strftime("%Y-%m-%d") + 'T23:59:59.999Z')

    return month_range


def get_time_range_wd(startTime, endTime, month=None):
    start_time = string_to_iso_date(startTime, default_month=1)
    end_time = string_to_iso_date(endTime, default_month=12)
    time_patterns = get_date_pattern(start_time, end_time, month)
    startDate = time_patterns[0]
    endDate = time_patterns[-1]
    startYear = startDate[0:4]
    startMonth = 1 if len(startDate) == 4 else int(startDate[4:6])
    endYear = endDate[0:4]
    endMonth = 12 if len(endDate) == 4 else int(endDate[4:6])

    startTime = string_to_iso_date(startYear, default_month=startMonth)
    endTime = string_to_iso_date(endYear, default_month=endMonth)
    time_ranges = get_utc_monthly_range(startTime, endTime, month)
    return time_ranges


def get_time_range_str(start_time, end_time, month, time_range: dict = None):
    if time_range is not None:
        list_values = list(time_range.values())
        return '_'.join(str(v) for v in list_values)
    else:
        time_range_str = start_time + '_' + end_time
        if month is not None:
            time_range_str += '_' + str(month).zfill(2)
        return time_range_str
