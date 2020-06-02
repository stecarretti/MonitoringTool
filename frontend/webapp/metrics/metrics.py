from google.cloud import firestore
from .metrics_utils import *


db = firestore.Client()


def get_snapshots(user_id, project_id):
    ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)\
        .collection(u'captured_snapshots').stream()
    s_list = [s.to_dict() for s in ref]
    return s_list


def compute(snap_list, timezone):
    hours = []
    delays = []
    days = []
    breakpoints = {}
    countries_summary = {}
    countries = {}
    for s in snap_list:
        create, final = s['create_final'].split('/')
        create = convert_time(create, timezone)
        final = convert_time(final, timezone)
        d = final - create
        seconds = d.seconds + d.days*24*60*60
        hours.append(get_hour(create))
        delays.append(seconds)
        days.append(get_day(create))
        try:
            breakpoints[s['breakpoint']] += 1
        except:
            breakpoints[s['breakpoint']] = 1
        ip = s['ip_address']
        if ip not in countries_summary:
            countries_summary[ip] = get_country(ip)
            try:
                countries[countries_summary[ip]] += 1
            except:
                countries[countries_summary[ip]] = 1
        else:
            countries[countries_summary[ip]] += 1
    return days, hours, delays, breakpoints, countries


def get_stats(user_id, project_id):
    timezone = db.collection(u'users').document(user_id).collection(u'projects').document(project_id).get().to_dict()['timezone']
    snap_list = get_snapshots(user_id, project_id)
    days, hours, delays, breakpoints, countries = compute(snap_list, timezone)
    # countries = {"FR": 1, "IT": 121}
    graph = mean_day_graph(hours, delays)
    return countries, breakpoints, graph


def get_graphs(user_id, project_id):
    timezone = db.collection(u'users').document(user_id).collection(u'projects').document(project_id).get().to_dict()[
        'timezone']
    snap_list = get_snapshots(user_id, project_id)
    days, hours, delays, breakpoints, countries = compute(snap_list, timezone)
    return days_graph(days, hours, delays)


if __name__ == '__main__':
    print(get_stats('stefano', 'chatroom-stefano-carretti'))

