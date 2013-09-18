import os
import sys
import json
import signal
import socket
import pprint
import urllib2
import requests
import threading
import subprocess

from iftranslator import shellquote
from iftranslator import OVSIFTranslator
from datetime import datetime as dt

from oscars_te.communicator import oscars
from oscars_te.runnable import Runnable
from oscars_te.monitor import FloodlightPortMonitor, FloodlightFlowMonitor

from oscars_te import app
log = app.logger

def updateMovingAverage(a, b, weight=.5):
    return (a[0]*weight+b[0]*(1-weight),a[1]*weight+b[1]*(1-weight))

class Trigger(Runnable):
    """Periodically monitor events and parse flows"""
    def __init__(self):
        super(Trigger, self).__init__()
        self._events = {}
        self._flows = []
        self._switches = {}
        self._hosts = {}
    
    def getSwitches(self):
        return self._switches

    def addSwitch(self, sw_name, sw_info):
        # self._switches[sw_name] = {
        #  'address':0.0.0.0, 
        #  'datapath': {
        #    '<dpname>': {
        #      '<port>' : {port_info}
        #    },
        #   'error': '<error message>'
        #  }}
        raise NotImplementedError

    def addHost(self, host_name, host_info):
        # self._hosts[host_name] = {
        #  'address':0.0.0.0, 
        #  'port': {
        #    'port_name': {
        #      'stats' : [
        #       {'RX':\d, 'TX':\d}
        #      ],
        #      'bandwidth': {
        #      'RX':\d, 'TX':\d
        #      }
        #    },
        #   'error': '<error message>'
        #  }}
        raise NotImplementedError

    def getEvents(self):
        """
        A Trigger Event happens when a policy is violated. For example,
        if the bandwidth flowing through an interface exceeds a given 
        threshold, an event should be generated
        """
        return self._events

    def registerEventListener(self):
        raise NotImplementedError

    def addEvent(self, event):
        #self._events = [event] + self._events
        self._events[event['id']] = event
        
    def getFlows(self):
        """
        Return a list of flows that associated with events 
        """
        return self._flows

    def actOnEvent(self):
        raise NotImplementedError


class SFlowCollector(Runnable):
    """SFlowCollector"""
    def __init__(self, path):
        super(SFlowCollector, self).__init__()
        self.path = path
    
    def run(self):
        """docstring for run"""
        try:
            log.debug('Starting collector at %s\n' % self.path)
            self._process = subprocess.Popen(self.path)
            log.debug('Started with pid %s\n' % str(self._process.pid))
            while not self.shouldStop():
                self.waitInterruptible(-1)
        except Exception, e:
            log.error('Could not start process: %s\n' % str(e))
        # try:
        #     os.killpg(self._process.pid, signal.SIGTERM)
        # except Exception, e:
        #     log.debug(
        #         'Could not stop process: %s\n' % str(e))
        self.terminate()

class SFlowTrigger(Trigger):
    """
    SFlowTrigger uses SFlow-RT to collect and parse sflow frames
    sent by switches.
    """
    def __init__(self, collector_url, collector_path=''):
        """
        The constructor for SFlowTrigger receives two parameters that 
        specify how to contact sflow-rt and another one (optional) 
        that specify where sflow-rt is installed. The later is optional,
        and if present SFlowTrigger will try to start the sflow-rt 
        collector using the given path.
        
        :param collector_url: where sflow-rt rest interface is running
        :param collector_path: 
        """
        super(SFlowTrigger, self).__init__()
        
        self.setUrl(collector_url)
        
        if collector_path and len(collector_path) > 0:
            self.collector = SFlowCollector(collector_path)
        else:
            self.collector = None
        
        self.addSwitch('ovs', '127.0.0.1')

    def addSwitch(self, sw_name, sw_address):
        datapath = {}
        error = ''
        try:
            datapath = OVSIFTranslator(sw_address)
        except Exception, e:
            log.error(str(e))
            error = str(e)
        
        self._switches[sw_name] = {
            'address': sw_address,
            'datapath': datapath,
            'error': error
        }
        
    def configureOVSSwitch(self):
        print 'sudo ovs-vsctl -- --id=@sflow create sflow agent=eth0 ' +\
            ' target=\"127.0.0.1:6343\" sampling=10 polling=20 -- -- set' + \
            ' bridge s1 sflow=@sflow'

    def registerLargeTCPEventListener(self, threshold_value=6000):
        flow = {
            'value':'frames',
            'keys':'ipsource,ipdestination,tcpsourceport,tcpdestinationport',
            'filter':'inputifindex=561'
        }
        threshold = {
            'metric': 'largeflow',
            'value': threshold_value, # what is large?
            'byFlow': 'true'
        }
        
        self.registerFlow('largeflow', flow)
        self.registerThreshold('largeflow', threshold)
    
    def registerEventListener(self, name, keys, switch, datapath, port, metric, by_flow, threshold):
        flow = {
            'value': str(metric),
            'keys': str(','.join(keys)),
            'filter':'inputifindex=%d' % int(port)
        }
        th = {
            'metric': str(name),
            'value': int(threshold),
            'byFlow': 'true' if by_flow else 'false'
        }
        log.debug('flow:' + str(flow) + '\n\n')
        log.debug('th:' + str(th) + '\n\n')
        self.registerFlow(str(name), flow)
        self.registerThreshold(str(name), th)
        
    def registerDefaultEventListener(self):
        """docstring for registerDefaultEventListener"""
        # Should we export this in the interface?
        group = {'external':['10.0.0.91/32'],'internal':['10.0.0.71/32']}
        flow = {
            'value':'frames',
            'keys':'ipsource,ipdestination',
            'filter':'sourcegroup=external&destinationgroup=internal'
        }
        threshold = {
            'metric':'incoming',
            'value':10
        }
        #self.registerEventListener(groups, flows, threshold)
        self.registerGroup(group)
        self.registerFlow('incoming', flow)
        self.registerThreshold('incoming', threshold)
    
    def registerThreshold(self, threshold_name, threshold_value):
        url = 'http://%s:%d' % (self._url['host'], self._url['port'])
        log.debug('Registering threshold %s\n' % str(threshold_value));
        r = requests.put('%s/threshold/%s/json' % (url, threshold_name),
                        data=json.dumps(threshold_value))
        log.debug(str(r) + '\n');
    
    def registerGroup(self, group_description):
        url = 'http://%s:%d' % (self._url['host'], self._url['port'])
        log.debug('Registering group %s\n' % str(group_description));
        r = requests.put('%s/group/json' % (url),
                        data=json.dumps(group_description))
        log.debug(str(r) + '\n');
        
    
    def registerFlow(self, flow_name, flow_description):
        url = 'http://%s:%d' % (self._url['host'], self._url['port'])
        log.debug('Registering flow %s\n' % str(flow_description));
        r = requests.put('%s/flow/%s/json' % (url, flow_name),
                        data=json.dumps(flow_description))
        log.debug(str(r) + '\n');
        
    def setUrl(self, url): 
        host,port = (url,8008)
        if len(host.split(':')) > 1:
            host,port = host.split(':')

        try:
            host = socket.gethostbyname(host)
            self._url = dict(host=str(host),port=int(port))
        except Exception:
            raise Exception('Could not resolve hostname.')

    def requestEvents(self, start_id=-1, timeout=1, total=10):
        """
        Request and return events from SFlowCollector in json format

        :param start_id: request only events with id > than start_id
        :param timeout: wait up to timeout seconds for result
        :param total: fetch at most max results
        """
        try:
            r = requests.get(
                'http://%s:%d/events/json?maxEvents=%d&timeout=%d&eventID=%d' % \
                (self._url['host'], self._url['port'], total, timeout, start_id))
            if r.status_code != 200:
                log.error("Return code = %d\n" % r.status_code )
            return r.json()
        except Exception, e:
            pass
        return ''
        
    def run(self):
        if self.collector:
            self.collector.start()

        maxTries = 10
        while maxTries > 0 and not self.shouldStop():
            try:
                log.debug('Registering default event listener...\n')
                #self.registerDefaultEventListener()
                self.registerLargeTCPEventListener()
                maxTries = -1
            except:
                self.waitInterruptible(2)
                maxTries -= 1
        if maxTries == 0 or self.shouldStop():
            self.stop()
            self.collector.stop()
            self.terminate()
            return

        last_event_id = -1;
        while not self.shouldStop():
            self.waitInterruptible(1)
            events = self.requestEvents(last_event_id)
            if len(events) == 0: continue
            
            last_event_id = events[0]["eventID"]
            for e in events:
                
                s = pprint.pformat(events)
                log.debug(s+'\n')
                
                e['id'] = e['eventID']
                self.addEvent(e)
                
                #if 'incoming' == e['metric']:
                r = requests.get('http://%s:%d/metric/%s/%s.%s/json' % \
                    (self._url['host'], self._url['port'], e['agent'],
                    e['dataSource'], e['metric']))
                metric = r.json()
                
                
                if len(metric) > 0:
                    #pprint.pformat(metric[0]["topKeys"][0]["key"])
                    s = pprint.pformat(metric)
                    log.debug('Metric:\n' + s +'\n')

        if self.collector:
            while not self.collector.isStopped():
                self.collector.stop()
        self.terminate()

class HostTrigger(Trigger):
    """docstring for HostTrigger"""
    def __init__(self):
        super(HostTrigger, self).__init__()
        self.registerHostEvent('mininet', '127.0.0.1', 'eth1', 400)
    
    def registerHostEvent(self, host_name, host_address, port, threshold):
        if not self._hosts.has_key(host_name):
            self._hosts[host_name] = {
                'port':{}, 
                'error':''}
        self._hosts[host_name]['address'] = host_address
        self._hosts[host_name]['port'][port] = {
            'stats':[],
            'threshold': threshold
        }
    def collectStats(self):
        script = \
            """
            ifconfig -a | grep -A7 HW | grep -E 'HW|TX by|RX by' | 
                awk '{ 
                    if ((NR % 2) == 1 ) {
                        printf "\\""$1"\\":{";
                    }
                    else {
                        printf "\\"RX\\":";
                        printf substr($2,7);
                        printf ",\\"TX\\":";
                        printf substr($6,7);
                        printf "}\\n" }}';
            """
        for host_name,host_info in self._hosts.iteritems():
            # This is not a good way to do this, but it is was fast to code
            cmd = 'ssh -o BatchMode=yes -o ConnectTimeout=1 %s %s' %\
                 (host_info['address'], shellquote(script))
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stdout=subprocess.PIPE)
            port_info = p.communicate()[0]
            stats = '{%s}' % ",".join(port_info.split('\n')[:-1])
            jstats = json.loads(stats)
            #print stats
            for port_name, port_info in host_info['port'].iteritems():
                if not jstats.has_key(port_name):
                    host_info['error'] = 'Could not find port %s' % port_name
                    continue
                if len(port_info['stats']) > 10:
                    port_info['stats'] = \
                        port_info['stats'][1:] + [jstats[port_name]]
                else:
                    port_info['stats'] += [jstats[port_name]]
            
            print host_name, host_info
            

    def run(self):
        while not self.shouldStop():
            self.collectStats()
            self.waitInterruptible(1)




class FloodlightTrigger(FloodlightPortMonitor, Trigger):
    """
    FloodlightTrigger
    
    This trigger monitors net device ports periodically and
    generate events when the threshold of event listeners are
    reached. Event listeners identify src and dst device and port,
    and could be configured to act (offload) the circuit 
    automatically. 
    """
    def __init__(self, controller_url, interval = 2, oscars_url=None):
        """
        :param controller_url: Floodlight controller url
        :param oscars_url: (optional) OSCARS database url. 
            NOTE that the OSCARS communicator will try to open a connection
            to OSCARS's mysql database with the username 'reader' and
            password 'reader'. Change this in the root config.py file
        :param interval: how frequently stats will be fetched from Floodlight
        """
        super(FloodlightTrigger, self).__init__(controller_url, interval)
        self._triggers = {};
        self.setOscarsURL(oscars_url)
        # self.registerEventListener(
        #     '00:00:00:00:00:00:00:01', '2', 1e3,
        #     '00:00:00:00:00:00:00:07', '2')
    
    def setOscarsURL(self, oscars_url):
        self._oscars_sync = 0; # to sync OSCARS circuits and event listeners
        self._oscars = None
        if not oscars_url:
            return;
        
        host,port = (oscars_url,3306)
        if len(host.split(':')) > 1:
            host = host.split(':')[0]

        try:
            host = socket.gethostbyname(host)
            self._oscars = dict(host=str(host),port=int(port))
            log.debug('Setting oscars_url to %s\n' % str(self._oscars))
        except Exception:
            raise Exception('Could not resolve oscars hostname.')
    
    def registerEventListener(self, sw_src_dpid, sw_src_port, threshold, sw_dst_dpid='', sw_dst_port=0, act = False, trigger_id=None):
        """
        Register an event listener with id = <sw_src_dpid>.<sw_src_port>.
        :param sw_src_dpid: Source node that the listener will monitor
        :param sw_src_port: Source port that the listener will monitor
        :param threshold: Threshold to generate an event
        :param sw_dst_dpid: Destination node to use when acting. 
                            The current action is to request OSCARS's a new
                            circuit with 10.5 times the configured threshold
        :param sw_dst_port: Destination port to use when acting.
        :param act: True if trigger is supposed to act automatically
        """
        if not trigger_id:
            trigger_id = '%s.%s' % (sw_src_dpid, sw_src_port)

        self._triggers[trigger_id] = {
            'id': trigger_id,
            'sw_src_dpid': sw_src_dpid,
            'sw_src_port': int(sw_src_port),
            'sw_dst_dpid': sw_dst_dpid,
            'sw_dst_port': int(sw_dst_port),
            'stats' : [],
            'bandwidth': (0,0), #moving average
            'threshold': int(threshold),
            'act': act,
            'error':''}
            
    def deleteEventListener(self, trigger_id):
        try:
            del self._triggers[trigger_id];
            del self._events[trigger_id];
        except:
            pass

    def actOnEvent(self, trigger_id):
        event = self._triggers[trigger_id]
        
        response = '{}'
        url = "http://%s:%d/create" % \
            (self._oscars['host'], self._oscars['port'])
        try:
            request = {
                'src-switch': event['sw_src_dpid'],
                'dst-switch': event['sw_dst_dpid'],
                'src-port': event['sw_src_port'],
                'dst-port': event['sw_dst_port'],
                'ofrule': 'dl_type=0x800',
                'bandwidth': event['threshold']*10.5,
                }
            response = requests.post(url, timeout=10).read();
            
        except Exception, e:
            raise Exception('Could not issue request: %s ' % e.message)
        return response

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
            log.warning('Could not fetch OSCARS circuits: %s\n' % str(e));
            pass
        
        log.debug('Trigger: fetched %d circuits form OSCARS\n' % len(circuits))
        
        active_ids = []
        sync_id = 0;
        for id, circuit in circuits.iteritems():
            # Only add event listener for circuits not seen before
            trigger_id = 'O.%s.%s' % \
                (circuit['hops'][0]['node'],circuit['hops'][0]['port'])
            active_ids += [trigger_id]
            
            if (self._oscars_sync < int(id)):
                if not self._triggers.has_key(trigger_id):
                    n_hops = len(circuit['hops'])
                    
                    log.debug("Registering new circuit %s.%s->%s.%s\n" %\
                    (
                        str(circuit['hops'][0]['node']),
                        str(circuit['hops'][0]['port']),
                        str(circuit['hops'][n_hops-1]['node']),
                        str(circuit['hops'][n_hops-1]['port'])
                    ))
                    
                    self.registerEventListener(
                        circuit['hops'][0]['node'],
                        circuit['hops'][0]['port'],
                        int(circuit['bandwidth'] * .5),
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
                log.debug('Removing %s\n'  % trigger_id)
                del self._triggers[trigger_id]

    def getRegisteredEvents(self):
        return self._triggers
        
    def requestStats(self):
        raw_stats  = super(FloodlightTrigger,self).requestStats()
        json_stats = json.loads(raw_stats)
        
        if self._oscars:
            self.syncOSCARSEventListeners()
        
        for trigger_id, trigger_info in self._triggers.items():
            trigger_dpid  = trigger_info['sw_src_dpid']
            trigger_port  = trigger_info['sw_src_port']
            trigger_stats = trigger_info['stats']

            if json_stats.has_key(trigger_dpid):
                for port in json_stats[trigger_dpid]:
                    if port['portNumber'] == trigger_port:
                        stats = (port['receiveBytes'], port['transmitBytes'])

                        if len(trigger_stats):
                            prev = (trigger_stats[-1])
                        else:
                            prev = stats

                        current_bw = (stats[0]-prev[0],stats[1]-prev[1])

                        if len(stats) > 10:
                            trigger_stats = trigger_stats[:-1] + [current_bw]
                        else:
                            trigger_stats += [current_bw]

                        trigger_info['bandwidth'] = updateMovingAverage(
                            trigger_info['bandwidth'], current_bw
                        )

            event = None
            if trigger_info['bandwidth'][0] > trigger_info['threshold']:
                event = {
                    "id": trigger_id,
                    "agent": trigger_info['sw_src_dpid'],
                    "flowKey": '%s,%s,%s,%s' % (
                        trigger_info['sw_src_dpid'],
                        trigger_info['sw_src_port'],
                        trigger_info['sw_dst_dpid'],
                        trigger_info['sw_dst_port']),
                    "value": int(trigger_info['bandwidth'][0])
                }

            if trigger_info['bandwidth'][1] > trigger_info['threshold']:
                # log.debug('TX Exceeded %s > %s\n' % \
                #     (trigger_info['bandwidth'][1], trigger_info['threshold']))
                
                event = {
                    "id": trigger_id,
                    "agent": trigger_info['sw_src_dpid'],
                    "flowKey": '%s,%s,%s,%s' % (
                        trigger_info['sw_src_dpid'],
                        trigger_info['sw_src_port'],
                        trigger_info['sw_dst_dpid'],
                        trigger_info['sw_dst_port']),
                    "value": int(trigger_info['bandwidth'][1])
                }
            if event:
                if trigger_info['act'] == True:
                    log.info('Act on event %s\n' % str(event))
                self.addEvent(event)
        # end for
                
        return raw_stats
    