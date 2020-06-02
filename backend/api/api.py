from flask import Flask, request
from flask_restful import Resource, Api
from monitoring import Monitoring

app = Flask(__name__)
api = Api(app)

host = 'debuggerbasedmonitoring.appspot.com'
basePath = '/api/v1'

monitoring = Monitoring()


class Breakpoint(Resource):
    def get(self, user_id, project_id):
        ret, content = monitoring.getBreakpoints(user_id, project_id)
        if not ret:
            return None, 400
        return content, 200

    def post(self, user_id, project_id):
        if request.is_json:
            body = request.get_json()
        else:
            return None, 409
        if 'content' not in body:
            return None, 409

        content = body['content']
        try:
            file, line = content.split(':')
            if isinstance(int(line), int):
                ret = monitoring.postBreakpoint(user_id, project_id, content)
                if ret:
                    return None, 201
                return None, 400
        except:
            return None, 409


class AllSnapshots(Resource):
    def get(self, user_id, project_id):
        ret, content = monitoring.getSnapshots(user_id, project_id)
        if not ret:
            return None, 400
        return content, 200


class Snapshot(Resource):
    def get(self, user_id, project_id, snapshot_id):
        ret, content = monitoring.getSnapshot(user_id, project_id, snapshot_id)
        if ret != 200:
            return None, ret
        return content, 200


class Measurements(Resource):
    def post(self, user_id, project_id):
        if request.is_json:
            body = request.get_json()
        else:
            return None, 409
        if 'setting' not in body:
            return None, 409

        setting = body['setting']
        if setting not in ['start', 'stop']:
            return None, 409
        if setting == 'start':
            ret = monitoring.startMeasurements(user_id, project_id)
            if ret:
                return None, 201
            return None, 400
        if setting == 'stop':
            ret = monitoring.stopMeasurements(user_id, project_id)
            if ret:
                return None, 201
            return None, 400


api.add_resource(Breakpoint, f'{basePath}/breakpoints/<string:user_id>/<string:project_id>')
api.add_resource(Snapshot, f'{basePath}/snapshots/<string:user_id>/<string:project_id>/<string:snapshot_id>')
api.add_resource(AllSnapshots, f'{basePath}/snapshots/<string:user_id>/<string:project_id>')
api.add_resource(Measurements, f'{basePath}/measurements/<string:user_id>/<string:project_id>')


if __name__ == "__main__":
    app.run(host='127.0.0.1', debug=True)
