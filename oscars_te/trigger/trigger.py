import os
import sys
import json
import signal
import socket
import pprint
import requests
import threading
import subprocess

from iftranslator import OVSIFTranslator
from datetime import datetime as dt

from oscars_te.runnable import Runnable

class Trigger(Runnable):
    """Periodically monitor events and parse flows"""
    def __init__(self):
        super(Trigger, self).__init__()
        self._events = []
        self._flows = []
        self._switches = {}
    
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
        self._events = [event] + self._events
        
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
            sys.stderr.write('Starting collector at %s\n' % self.path)
            self._process = subprocess.Popen(self.path)
            sys.stderr.write('Started with pid %s\n' % str(self._process.pid))
            while not self.shouldStop():
                self.waitInterruptible(-1)
        except Exception, e:
            sys.stderr.write('Could not start process: %s\n' % str(e))
        # try:
        #     os.killpg(self._process.pid, signal.SIGTERM)
        # except Exception, e:
        #     sys.stderr.write(
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
            sys.stderr.write(str(e))
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
    
    def registerEventListener(self, name, keys, switch, datapath,
                              port, metric, by_flow, threshold):
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
        sys.stderr.write('flow:' + str(flow) + '\n\n')
        sys.stderr.write('th:' + str(th) + '\n\n')
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
        sys.stderr.write('Registering threshold %s\n' % str(threshold_value));
        r = requests.put('%s/threshold/%s/json' % (url, threshold_name),
                        data=json.dumps(threshold_value))
        sys.stderr.write(str(r) + '\n');
    
    def registerGroup(self, group_description):
        url = 'http://%s:%d' % (self._url['host'], self._url['port'])
        sys.stderr.write('Registering group %s\n' % str(group_description));
        r = requests.put('%s/group/json' % (url),
                        data=json.dumps(group_description))
        sys.stderr.write(str(r) + '\n');
        
    
    def registerFlow(self, flow_name, flow_description):
        url = 'http://%s:%d' % (self._url['host'], self._url['port'])
        sys.stderr.write('Registering flow %s\n' % str(flow_description));
        r = requests.put('%s/flow/%s/json' % (url, flow_name),
                        data=json.dumps(flow_description))
        sys.stderr.write(str(r) + '\n');
        
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
                sys.stderr.write("Error, return code = %d\n" % r.status_code )
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
                sys.stderr.write('Registering default event listener...\n')
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
                sys.stderr.write(s+'\n')
                
                self.addEvent(e)
                
                #if 'incoming' == e['metric']:
                r = requests.get('http://%s:%d/metric/%s/%s.%s/json' % \
                    (self._url['host'], self._url['port'], e['agent'],
                    e['dataSource'], e['metric']))
                metric = r.json()
                
                
                if len(metric) > 0:
                    #pprint.pformat(metric[0]["topKeys"][0]["key"])
                    s = pprint.pformat(metric)
                    sys.stderr.write('Metric:\n' + s +'\n')

        if self.collector:
            while not self.collector.isStopped():
                self.collector.stop()
        self.terminate()
