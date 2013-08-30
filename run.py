import sys
import argparse

from oscars_te.monitor import FloodlightDefaultMonitor
from oscars_te import app
from flask.ext.bootstrap import Bootstrap

parser = argparse.ArgumentParser(description='OSCARS Traffic Engineering Application')

parser.add_argument('controller', action='store',
                    help='SDN Controller URL')

args = parser.parse_args()
app.debug = True

Bootstrap(app)

if app.debug == False and not app.config.has_key('controller'):
    app.config['controller'] = FloodlightDefaultMonitor(args.controller)
    app.config['controller'].start()

app.run(host='0.0.0.0')
app.config['controller'].stop()
    
