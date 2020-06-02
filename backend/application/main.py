from google.cloud import firestore
from threading import Thread
from datetime import datetime
import time
import requests
import pytz


URL_FOR_GET_SNAP_FUNCTION = 'https://us-central1-debuggerbasedmonitoring.cloudfunctions.net/check_snapshot'
URL_FOR_CREATE_SNAP_FUNCTION = 'https://us-central1-debuggerbasedmonitoring.cloudfunctions.net/create_snapshot'


def check_snapshot(body):
    from googleapiclient import discovery
    from google.oauth2 import service_account
    from google.cloud import firestore
    from datetime import datetime
    import pytz

    if 'user' not in body or 'project_id' not in body:
        return 'Wrong parameters', 409
    if 'snapshot_id' not in body or 'debuggee_id' not in body or 'breakpoint_id' not in body:
        return 'Wrong parameters', 409

    project_id = body['project_id']
    user = body['user']
    snap_id = body['snapshot_id']
    debuggee_id = body['debuggee_id']
    breakpoint_id = body['breakpoint_id']
    db = firestore.Client()
    p_ref = db.collection(u'users').document(user).collection(u'projects').document(project_id)
    if p_ref.get().exists:
        service_account_info = p_ref.get().to_dict()
    else:
        return 'Service account info not found', 411

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=['https://www.googleapis.com/auth/cloud-platform'])

    service = discovery.build('clouddebugger', 'v2', credentials=credentials)
    request = service.debugger().debuggees().breakpoints().get(debuggeeId=debuggee_id, breakpointId=snap_id)
    response = request.execute()['breakpoint']
    try:
        if response['isFinalState']:
            # store snapshot info
            snap_ref = p_ref.collection('captured_snapshots').document(snap_id)
            raw_ip = response['stackFrames'][3]['arguments'][1]['members'][15]['value']
            ip_address = raw_ip.split(', ')[0][1:]
            if not snap_ref.get().exists:
                snap_ref.set({
                    'create_final': response['createTime'] + '/' + response['finalTime'],
                    'breakpoint': breakpoint_id,
                    'ip_address': ip_address
                })
                # delete snapshot from running_snapshots
                p_ref.collection(u'running_snapshots').document(snap_id).delete()
            # create a new snapshot
            b_info = db.collection(u'users').document(user).collection(u'projects'). \
                document(project_id).collection(u'breakpoints').document(breakpoint_id).get().to_dict()
            body = {
                "action": "CAPTURE",
                "location": {
                    "path": b_info['file'],
                    "line": b_info['line']
                }}
            request = service.debugger().debuggees().breakpoints().set(debuggeeId=debuggee_id, body=body)
            snap_id = request.execute()['breakpoint']['id']
            print(snap_id, " created")
            tz = pytz.timezone("Zulu")
            snap_ref = p_ref.collection('running_snapshots').document(snap_id)
            snap_ref.set({
                u'id': snap_id,
                u'breakpoint_id': breakpoint_id,
                u'create_time': str(datetime.now(tz))
            })
            return 'All good bro', 201
    except Exception as e:
        print(e)
        return 'Probably Snapshot not captured yet', 202



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
                create_time = datetime.strptime(s_ref.get().to_dict()['create_time'], '%Y-%m-%d %H:%M:%S.%f%z')
                age = (now - create_time).days
                if (age > 0) or (s_ref.get().to_dict()['breakpoint_id'] in snap_done):
                    s_ref.delete()
                else:
                    snap_done[s_ref.get().to_dict()['breakpoint_id']] = snap.id
            # need to query again because it seems that once you loop over the query you cannot loop over it again
            breakpoints = p_ref.collection(u'breakpoints').stream()
            for b in breakpoints:
                d = b.to_dict()
            u_dict = u_ref.get().to_dict()
            p_dict = p_ref.get().to_dict()
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
                # in order not to wait until the execution of the function has finished
                Thread(target=requests.post, args=(URL_FOR_CREATE_SNAP_FUNCTION,), kwargs={'json': payload}).start()
            else:
                payload = {
                    "user": u_dict['name'],
                    "project_id": p_dict['project_id'],
                    "snapshot_id": snap_done[b.id],
                    "breakpoint_id": b.id,
                    "debuggee_id": p_dict['debuggee_id']
                }
                # Thread(target=requests.post, args=(URL_FOR_GET_SNAP_FUNCTION,), kwargs={'json': payload}).start()
                check_snapshot(payload)
