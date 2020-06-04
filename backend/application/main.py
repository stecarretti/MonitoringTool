from google.cloud import firestore
from threading import Thread
from datetime import datetime
import time
import requests
import pytz


URL_FOR_GET_SNAP_FUNCTION = 'https://us-central1-debuggermonitoring.cloudfunctions.net/check_snapshot'
URL_FOR_CREATE_SNAP_FUNCTION = 'https://us-central1-debuggermonitoring.cloudfunctions.net/create_snapshot'

db = firestore.Client()

while True:
    time.sleep(10)
    tz = pytz.timezone("Zulu")
    now = datetime.now(tz)
    users = db.collection(u'users').stream()
    for user in users:
        u_ref = db.collection(u'users').document(user.id)
        projects = u_ref.collection(u'projects').where(u'running', u'==', True).stream()
        for project in projects:
            p_ref = u_ref.collection(u'projects').document(project.id)
            snaps = p_ref.collection(u'running_snapshots').stream()
            breakpoints = p_ref.collection(u'breakpoints').stream()
            b_list = [b.id for b in breakpoints]
            snap_done = {}
            for snap in snaps:
                # ensure that only one snapshot per breakpoint is running
                s_ref = p_ref.collection(u'running_snapshots').document(snap.id)
                try:
                    create_time = datetime.strptime(s_ref.get().to_dict()['create_time'], '%Y-%m-%d %H:%M:%S.%f%z')
                    age = (now - create_time).days
                    if (age > 0) or (s_ref.get().to_dict()['breakpoint_id'] in snap_done):
                        s_ref.delete()
                    else:
                        snap_done[s_ref.get().to_dict()['breakpoint_id']] = snap.id
                except:
                    s_ref.delete()
            # need to query again because it seems that once you loop over the query you cannot loop over it again
            breakpoints = p_ref.collection(u'breakpoints').stream()
            u_dict = u_ref.get().to_dict()
            p_dict = p_ref.get().to_dict()
            for b in breakpoints:
                d = b.to_dict()
                if b.id not in snap_done:
                    # create one snapshot
                    payload = {
                        "user": u_dict['name'],
                        "project_id": p_dict['project_id'],
                        "snap_path": d['file'],
                        "snap_line": d['line'],
                        "breakpoint_id": b.id,
                        "debuggee_id": p_dict['debuggee_id']
                    }
                    Thread(target=requests.post, args=(URL_FOR_CREATE_SNAP_FUNCTION,), kwargs={'json': payload}).start()
                else:
                    payload = {
                        "user": u_dict['name'],
                        "project_id": p_dict['project_id'],
                        "snapshot_id": snap_done[b.id],
                        "breakpoint_id": b.id,
                        "debuggee_id": p_dict['debuggee_id']
                    }
                    Thread(target=requests.post, args=(URL_FOR_GET_SNAP_FUNCTION,), kwargs={'json': payload}).start()
