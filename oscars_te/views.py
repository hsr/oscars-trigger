import sys
from flask import request, render_template, jsonify, Response, send_from_directory, make_response
from oscars_te import app
from monitor import *
import plot
import json

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
    controller = request.args.get('controller','')
    oscarsdb = request.args.get('oscarsdb','')
    return render_template('intplot.html', controller=controller, oscarsdb=oscarsdb)


@app.route('/home')
@app.route('/')
def handleIndexRequest():
    return render_template('index.html')
    
@app.route('/about')
def handleAboutRequest():
    return render_template('about.html')
    
    
@app.route('/mon/flow')
def handleMonFlowRequest():
    try:
        stats = app.config['controller'].getLatestStats()
        return jsonify(json.loads(stats))
    except Exception, e:
        return e.message
        
@app.route('/mon/flow/all')
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
        path = app.static_folder+'/../';
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
    
def handleFloodlightTopologyRequest(controller):
    try:
        return plot.floodlight.get_topology(controller)
    except:
        return '[]';
    