import sys
from flask import request, render_template, jsonify, Response
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
    return render_template('graph.html', location=location, errormsg=errormsg)

@app.route('/')
def handleIndexRequest():
    return render_template('graph_options.html')
    
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