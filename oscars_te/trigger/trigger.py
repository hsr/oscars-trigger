import os
import sys
import json
import signal
import socket
import requests
import threading
import subprocess
from datetime import datetime as dt

from oscars_te.runnable import Runnable

class Trigger(Runnable):
    """Periodically monitor flows"""
    def __init__(self):
        super(Trigger, self).__init__()
        
    def getEvents(self):
        raise NotImplementedError
        
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
    """docstring for SFlowTrigger"""
    def __init__(self, collector_url, collector_path=''):
        super(SFlowTrigger, self).__init__()
        
        self.setUrl(collector_url)
        
        if len(collector_path):
            self.collector = SFlowCollector(collector_path)
        else:
            self.collector = None
        
    def configureOVSSwitch(self):
        print 'sudo ovs-vsctl -- --id=@sflow create sflow agent=eth0 ' +\
            ' target=\"127.0.0.1:6343\" sampling=10 polling=20 -- -- set' + \
            ' bridge s1 sflow=@sflow'

    def registerEventListener(self, groups, flows, threshold):
        """docstring for registerEventListener"""
        url = 'http://%s:%d' % (self._url['host'], self._url['port'])
        
        try:
            sys.stderr.write('Registering group ' + str(groups) + '\n');
            r = requests.put(url + '/group/json', data=json.dumps(groups))
            sys.stderr.write(str(r) + '\n');

            sys.stderr.write('Registering flows ' + str(flows) + '\n');
            r = requests.put(url + '/flow/incoming/json', data=json.dumps(flows))
            sys.stderr.write(str(r) + '\n');
        
            sys.stderr.write('Registering threshold ' + str(threshold) + '\n');
            r = requests.put(url + '/threshold/incoming/json', 
                data=json.dumps(threshold))
            sys.stderr.write(str(r) + '\n');
        except Exception, e:
            sys.stderr.write("Could not register event listener\n")
            sys.stderr.write(str(e) + '\n')

    
    def registerDefaultEventListener(self):
        """docstring for registerDefaultEventListener"""
        # Should we export this in the interface?
        groups = {'external':['10.0.0.91/32'],'internal':['10.0.0.71/32']}
        flows = {'value':'frames',
            'keys':'ipsource,ipdestination',
            'filter':'sourcegroup=external&destinationgroup=internal'}
        threshold = {'metric':'incoming','value':10}
        self.registerEventListener(groups, flows, threshold)
        
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
            #traceback.print_stack()
            pass
        return ''
        
    def run(self):
        if self.collector:
            self.collector.start()
            # give it sometime to start
            # TODO: we should check if agent is up instead of waiting
            # 2 seconds, because if it starts under load, it may not respond
            self.waitInterruptible(2)

        sys.stderr.write('Registering default event listener...\n')
        self.registerDefaultEventListener()
        
        
        last_event_id = -1;
        while not self.shouldStop():
            self.waitInterruptible(1)
            events = self.requestEvents(last_event_id)
            if len(events) == 0: continue
            
            sys.stderr.write(str(events))
            
            self.last_event_id = events[0]["eventID"]
            for e in events:
                if 'incoming' == e['metric']:
                    r = requests.get('http://%s:%d/metric/%s/%s.%s/json' % \
                        (self._url['host'], self._url['port'], e['agent'],
                        e['dataSource'], e['metric']))
                    metric = r.json()
                    if len(metric) > 0:
                        sys.stderr.write(metric[0]["topKeys"][0]["key"])

        if self.collector:
            while not self.collector.isStopped():
                self.collector.stop()
        self.terminate()
