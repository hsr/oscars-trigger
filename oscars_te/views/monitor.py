import sys
from oscars_te.monitor import FloodlightMonitor
import json
from oscars_te import app
from flask import Blueprint, render_template, Response, jsonify

bp = Blueprint('monitor', __name__, url_prefix='/monitor')

@bp.route('/')
@bp.route('/switch/<switch>')
def handleMonitorFlowRequest(switch=None):
    stats = ""
    try:
        if isinstance(app.config['controller_instance'], FloodlightMonitor):
            stats = app.config['controller_instance'].getLatestStats()
    except Exception, e:
        sys.stderr.write('Error:' + str(e.message))
        raise e
    return render_template('monitor.html', switch=switch, stats=stats);
    
@bp.route('/flow')
def handleMonFlowRequest():
    try:
        stats = app.config['controller_instance'].getLatestStats()
        return jsonify(json.loads(stats))
    except Exception, e:
        return e.message
        
@bp.route('/flow/all')
def handleMonFlowAllRequest():
    try:
        stats = app.config['controller'].getAllStats()
        sys.stderr.write(stats);
        # Remove single quotes from string and create a list from it
        stats = ','.join(stats.replace("'",'').split(','))
        return Response(stats, mimetype='application/json')
    except Exception, e:
        return e.message