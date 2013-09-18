import sys
import argparse

from oscarstrigger.monitor import FloodlightDefaultMonitor
from oscarstrigger.trigger import SFlowTrigger, HostTrigger, FloodlightTrigger
from oscarstrigger import app

parser = argparse.ArgumentParser(description='OSCARS Traffic Engineering Application')

parser.add_argument('--controller', action='store', default='localhost:8080',
                    help='SDN controller URL. Default: localhost:8080')

parser.add_argument('--oscars', action='store', default='localhost:3306',
                    help='OSCARS database URL. Default: localhost:3306')

parser.add_argument('--listener', action='store', default='localhost:9911',
                    help='OSCARS Listener URL. Default: localhost:9911')

parser.add_argument('--trigger', action='store', default='',
                    help='sFlow-RT URL. Default: localhost:8008')

parser.add_argument('--debug', action='store_true',
                    help='Enable debug mode')

args = parser.parse_args()

app.debug = False
if args.debug:
    app.debug = True

app.config['controller'] = args.controller;
app.config['oscars'] = args.oscars;
app.config['trigger'] = args.trigger;
app.config['listener'] = args.listener;

if app.debug is False \
    and not app.config.has_key('controller_instance') \
    and len(app.config['controller']) > 0:
    app.config['controller_instance'] = \
        FloodlightDefaultMonitor(app.config['controller'])
    app.config['controller_instance'].start()
else:
    app.config['controller_instance'] = None;
    
if app.debug is False \
    and not app.config.has_key('trigger_instance') \
    and len(app.config['trigger']) > 0:

    app.config['trigger_instance'] = FloodlightTrigger(
            controller_url=app.config['controller'],
            oscars_url=app.config['oscars'],
            listener_url=app.config['listener'],
            interval=3)
    # if app.config['trigger'] not in ['localhost', '127.0.0.1']:
    #     app.config['trigger_instance'] = \
    #         SFlowTrigger(app.config['trigger'], 
    #                      app.root_path + '/trigger/sflow-rt/start.sh')
    # else:
    #     app.config['trigger_instance'] = SFlowTrigger(app.config['trigger'])
    
    app.config['trigger_instance'].start()
else:
    app.config['trigger_instance'] = None;

if app.debug is False:
    import logging
    from logging import StreamHandler, Formatter
    app.logger.setLevel(logging.DEBUG)
    handler = StreamHandler(stream=sys.stderr)
    handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        # '[in %(pathname)s:%(lineno)d]'
        ))
    app.logger.addHandler(handler)

try:
    app.run(host='0.0.0.0')
except Exception, e:
    print 'Error: %s' % str(e)

if app.config['controller_instance']:
    app.config['controller_instance'].stop()

if app.config['trigger_instance']:
    app.config['trigger_instance'].stop()
