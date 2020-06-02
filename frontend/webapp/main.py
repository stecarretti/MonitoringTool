from flask import Flask, render_template, request
from google.cloud import firestore
from datetime import datetime
from utils import check_user_app
import json
import pytz
import numpy as np
from metrics.metrics import get_stats, get_graphs


app = Flask(__name__)
db = firestore.Client()

stats = None


@app.route('/delete/<user_id>/<project_id>')
def delete_project(user_id, project_id):
    u_ref = db.collection(u'users').document(user_id)
    p_ref = u_ref.collection(u'projects').document(project_id)
    b_list = p_ref.collection(u'breakpoints').stream()
    for b in b_list:
        b = p_ref.collection(u'breakpoints').document(b.id)
        b.delete()
    s1_list = p_ref.collection(u'captured_snapshots').stream()
    for s in s1_list:
        s = p_ref.collection(u'captured_snapshots').document(s.id)
        s.delete()
    s2_list = p_ref.collection(u'running_snapshots').stream()
    for s in s2_list:
        s = p_ref.collection(u'running_snapshots').document(s.id)
        s.delete()
    p_ref.delete()
    p_list = u_ref.collection(u'projects').stream()
    check = True
    for _ in p_list:
        check = False
    if check:
        u_ref.delete()
    return render_template('index.html')


@app.route('/logging/<user_id>', methods=['GET', 'POST'])
def add_project(user_id):
    if request.method == 'GET':
        return render_template('add_project.html', user_id=user_id)
    if request.method == 'POST':
        return logging()


@app.route('/stop_measurements/<user_id>/<project_id>')
def stop_measurements(user_id, project_id):
    ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
    ref.update({
        u'running': False
    })


@app.route('/start_measurements/<user_id>/<project_id>')
def start_measurements(user_id, project_id):
    ref = db.collection(u'users').document(user_id).collection(u'projects').document(project_id)
    ref.update({
        u'running': True
    })


@app.route('/metrics/<user_id>/<project_id>', methods=['GET'])
def metric(user_id, project_id):
    countries, breakpoints, mean_graph = get_stats(user_id, project_id)
    mean_graph = np.around([mean_graph[k] for k in mean_graph], decimals=3).tolist()
    return render_template('metric.html', user_id=user_id, project_id=project_id, countries=countries,
                           breakpoints=breakpoints, mean_graph=mean_graph)


@app.route('/metrics/<user_id>/<project_id>/plots', methods=['GET'])
def plots(user_id, project_id):
    week_graphs = get_graphs(user_id, project_id)
    week_graphs = [np.around([graph[k] for k in graph], decimals=3).tolist() for graph in week_graphs]
    return render_template('days_plots.html', user_id=user_id, project_id=project_id, graphs=week_graphs)


@app.route('/logging', methods=['GET', 'POST'])
def logging():
    if request.method == 'GET':
        timezones = pytz.all_timezones
        return render_template('logging.html', tzs=timezones)
    if request.method == 'POST':
        try:
            try:
                username = request.form['username']
                check_user = True
            except:
                username = request.form['hidden_username']
                check_user = False
            if len(username.split(' ')) != 1:
                return render_template('error.html', key='Error: username must be a single word')
            project_number = request.form['number']
            timezone = request.form['tz']
            keys = json.load(request.files['key_file'])
            project_id = keys['project_id']
            user_ref = db.collection(u'users').document(username)
            if check_user and user_ref.get().exists:
                return render_template('error.html', key='Error: username already existing')
            # try to access to user's application
            debuggee_id = check_user_app(keys, project_number, project_id)
            if not debuggee_id:
                print("Debuggee not found")
                return render_template('error.html', key="Error: your application is unreachable. "
                                                         "Check if all submissions are correct. If it's all corret, "
                                                         "it means that your application is not been used for too long. "
                                                         "Send a request to your application and try again")
            # if everything's good so far we can start adding data to firestore
            user_ref.set({
                u'create_time': datetime.now(),
                u'name': username
            })
            project_ref = user_ref.collection('projects').document(project_id)
            if project_ref.get().exists:
                return render_template('error.html', key='Error: Project already existing.')
            else:
                project_ref.set({
                    u'timezone': timezone,
                    u'project_number': project_number,
                    u'type': keys['type'],
                    u'project_id': keys['project_id'],
                    u'private_key_id': keys['private_key_id'],
                    u'private_key': keys['private_key'],
                    u'client_email': keys['client_email'],
                    u'client_id': keys['client_id'],
                    u'auth_uri': keys['auth_uri'],
                    u'token_uri': keys['token_uri'],
                    u'auth_provider_x509_cert_url': keys['auth_provider_x509_cert_url'],
                    u'client_x509_cert_url': keys['client_x509_cert_url'],
                    u'debuggee_id': debuggee_id,
                    u'running': True
                })
            try:
                breakpoints = request.form['breakpoints'].split('\r\n')
                file = []
                line = []
                for b in breakpoints:
                    f, l = b.split(':')
                    if isinstance(int(l), int):
                        file.append(f), line.append(l)
                    else:
                        raise Exception()
                # if no exeption is raised we can add data to firestore
                for i, b in enumerate(breakpoints):
                    b_ref = project_ref.collection('breakpoints').document(b)
                    b_ref.set({
                        u'file': file[i],
                        u'line': line[i],
                    })
            except:
                # delete user and project just created
                project_ref.delete()
                user_ref.delete()
                return render_template('error.html', key='Error: Breakpoints format not valid')
            return render_template('metrics_link.html', link=f'/metrics/{username}/{project_id}')
        except Exception as e:
            print(e)
            return render_template('error.html', key='Error: Missing input. Each field must be filled.')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    if request.method == 'POST':
        username = request.form['username']
        project = request.form['project']
        user_ref = db.collection(u'users').document(username).collection(u'projects').document(project)
        if not user_ref.get().exists:
            return render_template('error.html', key='Error: Username or project not existing')
        return render_template('metrics_link.html', link=f'/metrics/{username}/{project}')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)





