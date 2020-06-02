from urllib3 import PoolManager
import datetime
import pytz
import json
import numpy as np


def get_country(ip):
    url = 'http://ipinfo.io/' + ip + '/json'
    http = PoolManager()
    response = http.request('GET', url)
    data = json.loads(response.data)
    return data['country']


def get_hour(raw_time):
    return get_time(raw_time)[3]


def get_day(raw_time):
    return get_time(raw_time)[:3]


def get_time(timestamp):
    timestamp = timestamp.strftime("%Y:%m:%d:%H:%M:%S")
    return [int(x) for x in timestamp.split(':')]


def convert_time(timestamp, timezone):
    timestamp = datetime.datetime.strptime(timestamp[:-5], "%Y-%m-%dT%H:%M:%S")
    real_tz = pytz.timezone(timezone)
    std_tz = pytz.timezone("Etc/Zulu")
    tz_timestamp = std_tz.localize(timestamp).astimezone(real_tz)
    return tz_timestamp


# given a list of values, remove the outliers and calculate the mean
def rem_outliers_avg(data, m=1):
    data = np.array(data)
    data = data[abs(data - np.mean(data)) <= m * np.std(data)]
    return 1 / np.mean(data)


# returns an average of the day accesses
def mean_day_graph(hours, delays):
    if len(hours) != len(delays):
        return None
    d = {h: [] for h in range(24)}
    for i in range(len(hours)):
        d[hours[i]].append(delays[i])
    for k in d:
        if len(d[k]) > 0:
            d[k] = rem_outliers_avg(d[k])
        else:
            d[k] = 0
    return d


# returns an array containing the average for each day of the week, from Monday to Sunday
def days_graph(days, hours, delays):
    if len(hours) != len(delays) != len(days):
        return None
    ret = [{h: [] for h in range(24)} for _ in range(7)]
    not_done = [1 for _ in range(len(days))]
    arr = [[] for _ in range(7)]
    for i in range(len(days)):
        if not_done[i]:
            date = datetime.date(days[i][0], days[i][1], days[i][2])
            week_day = date.weekday()  # value from 0 to 6, from Monday to Sunday
            for j, x in enumerate(days):
                if x == days[i]:
                    arr[week_day].append(j)
            for k in arr[week_day]:
                not_done[k] = 0
    for i in range(7):
        h = [hours[k] for k in arr[i]]
        d = [delays[k] for k in arr[i]]
        ret[i] = mean_day_graph(h, d)
    # make sure that no empty array is returned
    return [{k: 0 for k in day} if day[0] == [] else day for day in ret]

