import sys
from flask import abort, request, render_template, jsonify, \
                    Response, send_from_directory, make_response
from oscars_te import app
from jinja2 import TemplateNotFound
from monitor import *
import plot
import json

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/plot')
def handlePlotRequest():
    oscarsdb = request.args.get('oscarsdb','')
    controller = request.args.get('controller','')
    location = request.args.get('location','')
    location = 'floodlight' if len(location) < 1 else location
    errormsg = plot.plot(controller, oscarsdb)
    return render_template('plot.html', location=location, errormsg=errormsg)

@app.route('/intplot')
def handleInteractivePlotRequest():
    controller = ''
    if app.config.has_key('controller'):
        controller = app.config['controller'];
    if len(request.args.get('controller','')) > 0:
        controller = request.args.get('controller','')

    oscars = request.args.get('oscars','')
    return render_template('intplot.html',
        controller=controller, oscarsdb=oscars)

@app.route('/', defaults={'page': 'index'})
@app.route('/<page>')
def handlePageRequest(page):
    try:
        return render_template('%s.html' % page)
    except TemplateNotFound:
        abort(404)

@app.route('/monitor')
@app.route('/monitor/switch/<switch>')
def handleMonitorFlowRequest(switch=None):
    stats = ""
    try:
        if isinstance(app.config['controller_instance'], FloodlightMonitor):
            stats = app.config['controller_instance'].getLatestStats()
    except Exception, e:
        pass
    return render_template('monitor.html', switch=switch, stats=stats);
    
@app.route('/monitor/flow')
def handleMonFlowRequest():
    try:
        stats = app.config['controller_instance'].getLatestStats()
        return jsonify(json.loads(stats))
    except Exception, e:
        return e.message
        
@app.route('/monitor/flow/all')
def handleMonFlowAllRequest():
    try:
        stats = app.config['controller'].getAllStats()
        # Remove single quotes from string and create a list from it
        stats = ','.join(stats.replace("'",'').split(','))
        return Response(stats, mimetype='application/json')
    except Exception, e:
        return e.message

def readStaticFile(filename, path=''):
    if not len(path):
        path = app.static_folder+'/../'; #TODO: is there any "app.root" ?
    return make_response(send_from_directory(path,filename))

@app.route('/data/circuits.json')
def handleNoCacheCircuits():
    oscarsdb = request.args.get('oscarsdb','')
    if len(oscarsdb) > 2:
        reply = plot.oscars.get_active_circuits(oscarsdb)
        reply = '[%s]' % ','.join(reply.split('\n')[:-1])
        resp = Response(reply, mimetype='application/json')
    else:
        resp = readStaticFile(request.path[1:])
    resp.cache_control.no_cache = True
    return resp

@app.route('/data/topology.json')
def handleNoCacheTopology():
    controller = request.args.get('controller', '')
    if len(controller) > 1:
        reply = plot.floodlight.get_topology(controller)
        resp = Response(reply, mimetype='application/json')
    else:
        resp = readStaticFile(request.path[1:])
    resp.cache_control.no_cache = True
    return resp    