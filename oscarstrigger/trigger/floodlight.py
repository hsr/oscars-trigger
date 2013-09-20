import time
import json
import socket
import requests
import pprint

from oscarstrigger.monitor import FloodlightPortMonitor
from oscarstrigger.trigger import Trigger
from oscarstrigger.trigger import movingAverage

from oscarstrigger.communicator import oscars

from config import EVENT_LISTENER_THRESHOLD, EVENT_LISTENER_BANDWIDTH, EVENT_LISTENER_MOVING_AVERAGE_W

from oscarstrigger import app
log = app.logger


class FloodlightTrigger(FloodlightPortMonitor, Trigger):
    """
    FloodlightTrigger
    
    This trigger monitors net device ports periodically and
    generate events when the threshold of event listeners are
    reached. Event listeners identify src and dst device and port,
    and could be configured to act (offload) the circuit 
    automatically. 
    """
    def __init__(self, controller_url, oscars_url=None, listener_url=None, interval = 2):
        """
        :param controller_url: Floodlight controller url
        :param oscars_url: (optional) OSCARS database url. 
            NOTE that the OSCARS communicator will try to open a connection
            to OSCARS's mysql database with the username 'reader' and
            password 'reader'. Change this in the root config.py file
        :param listener_url: (optional) OSCARS Listener url. 
        :param interval: how frequently stats will be fetched from Floodlight
        """
        super(FloodlightTrigger, self).__init__(controller_url, interval)
        self._triggers = {};
        
        self._oscars_sync = 0; # to sync OSCARS circuits and event listeners
        
        self._oscars = self.getURL(oscars_url, default_port=3306)
        self._listener = self.getURL(listener_url, default_port=9911)
        
        # self.registerEventListener(
        #     '00:00:00:00:00:00:00:01', '2', 1e3,
        #     '00:00:00:00:00:00:00:07', '2')
    
    def getURL(self, url=None, default_port=3306):
        if not url:
            return None;
        
        host,port = (url,default_port)
        if len(host.split(':')) == 2:
            host,port = host.split(':')

        try:
            host = socket.gethostbyname(host)
            return dict(host=str(host),port=int(port))
        except Exception:
            log.warning('Could not resolve hostname %s' % host)
        return None
    
    def registerEventListener(self, src_dpid, src_port, threshold, dst_dpid='', dst_port=0, act = False, trigger_id=None):
        """
        Register an event listener with id = <src_dpid>.<src_port>.
        :param src_dpid: Source node that the listener will monitor
        :param src_port: Source port that the listener will monitor
        :param threshold: Threshold to generate an event
        :param dst_dpid: Destination node to use when acting. 
                            The current action is to request OSCARS's a new
                            circuit with 20 times the configured threshold
        :param dst_port: Destination port to use when acting.
        :param act: True if trigger is supposed to act automatically
        """
        src_dpid = src_dpid.replace('.',':')
        dst_dpid = dst_dpid.replace('.',':')
        
        if not trigger_id:
            trigger_id = '%s.%s' % (src_dpid, src_port)

        log.debug("Registering event listener %s %s.%s->%s.%s" % \
            (trigger_id, src_dpid, src_port, dst_dpid, dst_port))

        self._triggers[trigger_id] = {
            'id': trigger_id,
            'src_dpid': src_dpid,
            'src_port': int(src_port),
            'dst_dpid': dst_dpid,
            'dst_port': int(dst_port),
            'stats' : [],
            'time': [],
            'bandwidth': (0,0), #moving average
            'threshold': int(threshold),
            'act': act,
            'offloaded': False,
            'error':''}
            
    def deleteEventListener(self, trigger_id):
        try:
            del self._triggers[trigger_id];
            del self._events[trigger_id];
        except:
            pass

    def actOnEvent(self, trigger_id):
        elistener = self._triggers[trigger_id]
        
        if not self._listener:
            return
        log.warning('Acting on event %s' % str(elistener))
        
        response = '{}'
        url = "http://%s:%d/request" % \
            (self._listener['host'], self._listener['port'])
        try:
            request = {
                'src-switch': elistener['src_dpid'].replace(':','.'),
                'dst-switch': elistener['dst_dpid'].replace(':','.'),
                'src-port': elistener['src_port'],
                'dst-port': elistener['dst_port'],
                'ofrule': 'nw_proto=17',
                'bandwidth': elistener['threshold'] * EVENT_LISTENER_BANDWIDTH,
                }
            request = json.dumps(request);
            response = requests.post(url, data=request, timeout=10);
        except Exception, e:
            log.warning('Could not issue request: %s ' % e.message)
        log.info('Offloading reponse: %s' % response);
        
        elistener['act'] = False;
        elistener['offloaded'] = True;
        try:
            del self._events[trigger_id]
        except:
            pass

    def syncOSCARSEventListeners(self):
        """
        Creates one event listener (trigger) for each OSCARS circuit using
        OSCARS circuits' end points
        """
        circuits = {}
        try:
            oscarsdb = '%s:%d' % (self._oscars['host'],self._oscars['port'])
            circuits = oscars.get_circuits_by_status(oscarsdb=oscarsdb);
        except Exception, e:
            log.warning('Could not fetch OSCARS circuits: %s' % str(e));
            pass
        
        log.debug('Trigger: fetched %d circuits form OSCARS' % len(circuits))
        
        active_ids = []
        sync_id = 0;
        for id, circuit in circuits.iteritems():
            # Only add event listener for circuits not seen before
            trigger_id = 'OSCARS.%s.%s' % \
                (circuit['hops'][0]['node'].replace('.', ':'),
                 circuit['hops'][0]['port'])
            active_ids += [trigger_id]
            
            if (self._oscars_sync < int(id)):
                if not self._triggers.has_key(trigger_id):
                    n_hops = len(circuit['hops'])
                    
                    self.registerEventListener(
                        circuit['hops'][0]['node'],
                        circuit['hops'][0]['port'],
                        int(circuit['bandwidth'] * EVENT_LISTENER_THRESHOLD),
                        circuit['hops'][n_hops-1]['node'],
                        circuit['hops'][n_hops-1]['port'],
                        act=True,
                        trigger_id=trigger_id)

                sync_id = max(sync_id,int(id))
        # end for
        
        # Only sync
        self._oscars_sync = \
            max(sync_id, self._oscars_sync)
            
        # Delete event listener related to finished/cancelled circuits
        for trigger_id in self._triggers.keys():
            if trigger_id[0] == 'O' and trigger_id not in active_ids:
                log.debug('Removing %s'  % trigger_id)
                try:
                    del self._triggers[trigger_id]
                    del self._events[trigger_id]
                except (Exception, e):
                    log.debug('Error removing event %s', str(e))

    def getRegisteredEvents(self):
        return self._triggers
        
    def requestStats(self):
        raw_stats  = super(FloodlightTrigger,self).requestStats()
        json_stats = json.loads(raw_stats)
        
        if self._oscars:
            self.syncOSCARSEventListeners()
        
        for trigger_id, trigger_info in self._triggers.items():
            # Check stats for each registered event listeners
            trigger_dpid  = trigger_info['src_dpid']
            trigger_port  = trigger_info['src_port']
            trigger_stats = trigger_info['stats']
            trigger_time  = trigger_info['time']

            # s = pprint.pformat(trigger_info)
            # log.debug(s)

            if json_stats.has_key(trigger_dpid):
                # Search port
                for port in json_stats[trigger_dpid]:
                    if port['portNumber'] == trigger_port:
                        # Calculate stats
                        stats = (port['receiveBytes'], port['transmitBytes'])
                        now = time.time()

                        if len(trigger_stats):
                            prev_stats = trigger_stats[-1]
                            prev_time  = trigger_time[-1]
                        else:
                            prev_stats = stats
                            prev_time  = now
                        
                        if prev_time != now:
                            elapsed   = now - prev_time
                            bandwidth = (8*((stats[0]-prev_stats[0])/elapsed),
                                         8*((stats[1]-prev_stats[1])/elapsed))
                        else:
                            bandwidth = (0,0)
                            
                        if len(trigger_stats) > 4:
                            trigger_info['stats'] = trigger_stats[1:] + [stats]
                            trigger_info['time']  = trigger_time[1:] + [now]
                        else:
                            trigger_info['stats'] += [stats]
                            trigger_info['time']  += [now]

                        trigger_info['bandwidth'] = movingAverage(
                            trigger_info['bandwidth'], bandwidth, 
                            weight=EVENT_LISTENER_MOVING_AVERAGE_W)

            violation = None
            if trigger_info['bandwidth'][0] > trigger_info['threshold']:
                violation = trigger_info['bandwidth'][0]
            if trigger_info['bandwidth'][1] > trigger_info['threshold']:
                violation = trigger_info['bandwidth'][1]
            
            if trigger_info['offloaded'] is True:
                violation = None
                
            if violation:
                event = {
                    "id": trigger_id,
                    "agent": trigger_info['src_dpid'],
                    "flowKey": '%s,%s,%s,%s' % (
                        trigger_info['src_dpid'],
                        trigger_info['src_port'],
                        trigger_info['dst_dpid'],
                        trigger_info['dst_port']),
                    "value": int(violation)
                }
                
                self.addEvent(event)
                if trigger_info['act'] == True:
                    self.actOnEvent(trigger_id)
        # end for
        return raw_stats
    
