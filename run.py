import sys
import argparse

from oscars_te.monitor import FloodlightDefaultMonitor
from oscars_te import app

parser = argparse.ArgumentParser(description='OSCARS Traffic Engineering Application')

parser.add_argument('controller', action='store',
                    help='SDN Controller URL')

args = parser.parse_args()

if not app.config.has_key('controller'):
    app.config['controller'] = FloodlightDefaultMonitor(args.controller)

app.config['controller'].start()
#app.debug = True
app.run(host='0.0.0.0')
app.config['controller'].stop()
    


