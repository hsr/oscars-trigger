import sys
from flask import request, render_template
from oscars_te import app

import plot 


@app.route('/plot')
def handlePlotRequest():
    oscarsdb = request.args.get('oscars','')
    controller = request.args.get('controller','')
    location = request.args.get('location','')
    location = 'floodlight' if len(location) < 1 else location
    errormsg = plot.plot(controller, oscarsdb)
    return render_template('graph.html', location=location, errormsg=errormsg)

@app.route('/')
def handleIndexRequest():
    return render_template('graph_options.html')