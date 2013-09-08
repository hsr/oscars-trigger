import sys
import argparse

from oscars_te.monitor import FloodlightDefaultMonitor
from oscars_te.trigger import SFlowTrigger
from oscars_te import app
from flask.ext.bootstrap import Bootstrap

parser = argparse.ArgumentParser(description='OSCARS Traffic Engineering Application')

parser.add_argument('--controller', action='store', default='localhost:8080',
                    help='SDN controller URL. Default: localhost:8080')

parser.add_argument('--oscars', action='store', default='localhost:3306',
                    help='OSCARS database URL. Default: localhost:3306')

parser.add_argument('--trigger', action='store', default='',
                    help='sFlow-RT URL. Default: localhost:8008')

parser.add_argument('--debug', action='store_true',
                    help='Enable debug mode')

args = parser.parse_args()

app.debug = False
if args.debug:
    app.debug = True

Bootstrap(app)

app.config['controller'] = args.controller;
app.config['oscars'] = args.oscars;
app.config['trigger'] = args.trigger;

if app.debug == False and not app.config.has_key('controller_instance'):
    app.config['controller_instance'] = \
        FloodlightDefaultMonitor(app.config['controller'])
    sys.stderr.write('Starting Floodlight monitor...\n')
    app.config['controller_instance'].start()
else:
    app.config['controller_instance'] = None;
    
if app.debug == False and not app.config.has_key('trigger_instance'):
    if len(app.config['trigger']) > 0:
        app.config['trigger_instance'] = \
            SFlowTrigger(
                app.config['trigger'], 
                app.root_path + '/trigger/sflow-rt/start.sh')
        app.config['trigger_instance'].start()
else:
    app.config['trigger_instance'] = None;


app.run(host='0.0.0.0')

if app.config['controller_instance']:
    app.config['controller_instance'].stop()

if app.config['trigger_instance']:
    app.config['trigger_instance'].stop()