from oscars_te import communicator
from flask import Blueprint, render_template, Response, request, send_file

bp = Blueprint('data', __name__, url_prefix='/data')

@bp.route('/circuits.json')
def handleNoCacheCircuits():
    oscarsdb = request.args.get('oscarsdb','')
    if len(oscarsdb) > 2:
        reply = communicator.oscars.get_active_circuits(oscarsdb)
        reply = '[%s]' % ','.join(reply.split('\n')[:-1])
        resp = Response(reply, mimetype='application/json')
    else:
        resp = send_file(request.path[1:])
    resp.cache_control.no_cache = True
    return resp

@bp.route('/topology.json')
def handleNoCacheTopology():
    controller = request.args.get('controller', '')
    if len(controller) > 1:
        reply = communicator.floodlight.get_topology(controller)
        resp = Response(reply, mimetype='application/json')
    else:
        resp = send_file(request.path[1:])
    resp.cache_control.no_cache = True
    return resp    