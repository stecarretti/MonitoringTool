from google.cloud import firestore

db = firestore.Client()


class Monitoring:
    def getBreakpoints(self, user_id, project_id):
        p_ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
        if not p_ref.get().exists:
            return False, None
        ref = p_ref.collection(u'breakpoints').stream()
        return True, [b.id for b in ref]

    def postBreakpoint(self, user_id, project_id, breakpoint_id):
        p_ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
        if not p_ref.get().exists:
            return False
        b_ref = p_ref.collection(u'breakpoints').document(breakpoint_id)
        if not b_ref.get().exists:
            file, line = breakpoint_id.split(':')
            b_ref.set({
                u'file': file,
                u'line': line
            })
        return True

    def getSnapshots(self, user_id, project_id):
        p_ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
        if not p_ref.get().exists:
            return False, None
        ref = p_ref.collection(u'captured_snapshots').stream()
        return True, [s.id for s in ref]

    def getSnapshot(self, user_id, project_id, snapshot_id):
        p_ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
        if not p_ref.get().exists:
            return 400, None
        s_ref = p_ref.collection(u'captured_snapshots').document(snapshot_id).get()
        if s_ref.exists:
            return 200, s_ref.to_dict()
        return 404, None

    def startMeasurements(self, user_id, project_id):
        ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
        if ref.get().exists:
            ref.update({
                u'running': True
            })
            return True
        return False

    def stopMeasurements(self, user_id, project_id):
        ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
        if ref.get().exists:
            ref.update({
                u'running': False
            })
            return True
        return False
