from download.interface.iinput import InputStrategy


# depth information is not necessary
def get_depth(workingDomain):
    """
    @param workingDomain: dict with depth information:
                depth: depth range in string format: [minDepth, maxDepth]
    @return: depth range in string format: [minDepth, maxDepth]
    """
    if 'depth' not in workingDomain:
        return None

    depth = workingDomain['depth']

    if depth is None:
        raise Exception("Can't extract vertical domain from wd: " + str(workingDomain))
    return depth


# lonLat information is not necessary
def get_lon_lat(workingDomain):
    """
    @param workingDomain: dict with lonLat information:
                lonLat: list of list, the internal list has the format:  [minLon , maxLon, minLat , maxLat]
    @return: a lonLat represent as a list of float with the template:
                [minLon , maxLon, minLat , maxLat]
    """
    return workingDomain['lonLat']


def extract_year(input_date):
    if isinstance(input_date, str):
        year = int(input_date[0:4])
    else:
        raise Exception("Can't extract year from data type: {}", type(input_date))

    return year


def extract_month(input_date):
    if isinstance(input_date, str):
        month = int(input_date[5:7])
    else:
        raise Exception("Can't extract month from data type: {}", type(input_date))

    return month


def extract_day(input_date):
    if isinstance(input_date, str):
        day = int(input_date[8:10])
    else:
        raise Exception("Can't extract day from data type: {}", type(input_date))

    return day


def get_number_day_in_month(year, month):
    from calendar import monthrange
    return monthrange(year, month)[1]  # to get the correct last day of end_month


def generate_time_list(start_time, end_time, time_freq):
    import pandas

    from datetime import date

    time_list = list()

    start_year = int(start_time[0:4])
    end_year = int(end_time[0:4])
    start_month = 1
    end_month = 12
    start_day = 1
    end_day = 31

    if time_freq == "y":
        pass  # the default parameters are okay
    elif time_freq == "m":
        start_month = extract_month(start_time)
        end_month = extract_month(end_time)
        end_day = get_number_day_in_month(end_year, end_month)
    elif time_freq == "d":
        start_month = extract_month(start_time)
        end_month = extract_month(end_time)
        start_day = extract_day(start_time)
        end_day = get_number_day_in_month(end_year, end_month)
    else:
        raise Exception("Time resolution {} unknown".format(time_freq))

    sdate = date(start_year, start_month, start_day)  # start date
    edate = date(end_year, end_month, end_day)  # end date

    pandas_time_list = pandas.date_range(sdate, edate, freq=time_freq)
    for time in pandas_time_list:
        year = time.year
        month = str(time.month).zfill(2)
        day = time.day

        if time_freq == "y":
            new_date = "{}".format(year)
        elif time_freq == "m":
            new_date = "{}{}".format(year, month)
        elif time_freq == "d":
            new_date = "{}{}{}".format(year, month, day)
        else:
            raise Exception("Time resolution {} unknown".format(time_freq))

        time_list.append(new_date)
    return time_list


def get_time(workingDomain, freq):
    """
    Check if the time range refers to the same month, then return the date with the pattern YYYYMM
    @param workingDomain: dict with time information:
            time: date in string format: [YYYYMM]
    @return a list of date with pattern YYYYMM
    """
    if 'time' not in workingDomain:
        raise Exception("Can't read time from workingDomain")
    time = workingDomain['time']
    # extract time as YYYYMM
    start_time = time[0]
    end_time = time[1]

    time_list = generate_time_list(start_time, end_time, freq)
    # check if only one month has been requested
    # if start_time != end_time:
    #     raise Exception("time error, check the time range: " + start_time + " - " + end_time)

    return time_list


class InStHub(InputStrategy):
    def __init__(self, time_freq="m"):
        self.lonLat = None
        self.depth = None
        self.time = None
        self.time_freq = time_freq

    def get_wd(self, workingDomain, dataset):
        """
        @param dataset: source dataset
        @param workingDomain: dict with spatial/time information:
                lonLat: list of list, the internal list has the format:  [[minLon , maxLon], [minLat , maxLat]]
                depth: depth range in string format: [minDepth, maxDepth]
                time: list of two strings that represent a time range: [YYYY-MM-DDThh:mm:ssZ, YYYY-MM-DDThh:mm:ssZ]
        @return: a new working domain with the format required to download from hda
        """
        self.lonLat = get_lon_lat(workingDomain)
        self.depth = get_depth(workingDomain)
        self.time = get_time(workingDomain, self.time_freq)
        return self.__dict__

    def get_wd_from_string_template(self, string_template):
        pass
