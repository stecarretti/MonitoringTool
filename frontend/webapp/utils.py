from googleapiclient import discovery
from google.oauth2 import service_account


def check_user_app(keys, project_number, project_id):
    credentials = service_account.Credentials.from_service_account_info(
        keys,
        scopes=['https://www.googleapis.com/auth/cloud-platform'])

    service = discovery.build('clouddebugger', 'v2', credentials=credentials)
    debuggees = service.debugger().debuggees().list(project=project_id, includeInactive=True).execute()
    debuggee_id = None
    for d in debuggees['debuggees']:
        try:
            if not d['isInactive']:
                debuggee_id = d['id']
        except:
            if d['project'] == project_number:
                debuggee_id = d['id']
    return debuggee_id
