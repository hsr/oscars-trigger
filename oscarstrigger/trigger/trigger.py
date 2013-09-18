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

from oscarstrigger.runnable import Runnable

from oscarstrigger import app
log = app.logger

def movingAverage(a, b, weight=.5):
    """
    Given two tuples with 2 values each (for TX and RX), return the weighted
    average of these numbers.
    
    :param a: tuple with two values (for TX and RX)
    :param b: tuple with two values (for TX and RX)
    :param weight: weight for b (1-weight for a)
    """
    return (a[0]*(1.-weight)+b[0]*weight,a[1]*(1.-weight)+b[1]*weight)

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




