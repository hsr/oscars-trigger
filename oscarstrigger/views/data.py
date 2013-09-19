from oscarstrigger import communicator
from flask import Blueprint, render_template, Response, request, send_file
import json

from oscarstrigger import app
log = app.logger

bp = Blueprint('data', __name__, url_prefix='/data')

@bp.route('/circuits.json')
def handleNoCacheCircuits():
    oscarsdb = request.args.get('oscarsdb','')
    try:
        if len(oscarsdb) > 2:
            reply = communicator.oscars.get_active_circuits(oscarsdb)
            reply = '[%s]' % ','.join(reply.split('\n')[:-1])
            resp = Response(reply, mimetype='application/json')
        else:
            resp = send_file('static' + request.path)
    except Exception, e:
        log.warning('Could not fetch circuits: %s', str(e))
        resp = Response(json.loads('[]'), mimetype='application/json')
        
    resp.cache_control.no_cache = True
    return resp

@bp.route('/topology.json')
def handleNoCacheTopology():
    controller = request.args.get('controller', '')
    try:
        if len(controller) > 1:
            reply = communicator.floodlight.get_topology(controller)
            resp = Response(reply, mimetype='application/json')
        else:
            resp = send_file('static' + request.path)
    except Exception, e:
        log.warning('Could not fetch topology: %s', str(e))
        resp = Response(json.loads('{}'), mimetype='application/json')
        
    resp.cache_control.no_cache = True
    return resp    
