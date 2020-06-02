
def check_snapshot(request):
    from googleapiclient import discovery
    from google.oauth2 import service_account
    from google.cloud import firestore
    from datetime import datetime
    import pytz

    if request.method == 'POST':
        if request.is_json:
            body = request.get_json(silent=True)
        else:
            return 'json not found', 400

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
                b_info = db.collection(u'users').document(user).collection(u'projects').\
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
    return 'Nothing done', 200


def create_snapshot(request):
    from googleapiclient import discovery
    from google.oauth2 import service_account
    from google.cloud import firestore
    from datetime import datetime
    import pytz

    if request.method == 'POST':
        print('All good')
        request_json = request.get_json(silent=True)
        print('json good')
        if request_json:
            body = request_json
        else:
            return '', 404
        print('body good')
        if 'user' not in body or 'project_id' not in body:
            return 'Wrong parameters', 409
        if 'snap_path' not in body or 'debuggee_id' not in body or 'breakpoint_id' not in body:
            return 'Wrong parameters', 409

        project_id = body['project_id']
        user = body['user']
        snap_body = {
            "action": "CAPTURE",
            "location": {
                "path": body['snap_path'],
                "line": body['snap_line']
            },
        }
        debuggee_id = body['debuggee_id']
        breakpoint_id = body['breakpoint_id']
        db = firestore.Client()
        ref = db.collection(u'users').document(user).collection(u'projects').document(project_id)
        if ref.get().exists:
            service_account_info = ref.get().to_dict()
        else:
            return 'Service account info not found', 411

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform'])

        service = discovery.build('clouddebugger', 'v2', credentials=credentials)
        request = service.debugger().debuggees().breakpoints().set(debuggeeId=debuggee_id, body=snap_body)
        snap_id = request.execute()['breakpoint']['id']
        print(snap_id, " created")
        tz = pytz.timezone("Zulu")
        snap = ref.collection('running_snapshots').document(snap_id)
        snap.set({
            u'id': snap_id,
            u'breakpoint_id': breakpoint_id,
            u'create_time': str(datetime.now(tz))
        })
        return 'All good bro', 201
    return 'Nothing done', 200

