import os
import re
import sys
import json
import signal
import socket
import requests
import threading
import subprocess
from datetime import datetime as dt

def shellquote(s):
    return "'" + s.replace("'", "'\\''") + "'"

class IFTranslator(dict):
    """
    IFTranslator is a dictionary, indexed by switch DPID that
    provides translations between interfaces names/numbers/indexes
    """
    def __init__(self):
        super(IFTranslator, self).__init__()
    
    def translate(self, sw, port):
        """docstring for translate"""
        raise NotImplementedError
        
        
class OVSIFTranslator(IFTranslator):
    """
    Translates OVS IfIndex numbers to OpenFlow ports using ssh/bash
    
    Pre-requisites:
        - passwordless ssh access to host where OVS is running
        - read access to files under /sys/devices/virtual/net/ 
    """
    def __init__(self, host='127.0.0.1'):
        """
        :param host: the ip address of the host running OVS
        """
        super(OVSIFTranslator, self).__init__()
        self._host = host
        self.updateInfo()

    def fetchPortInfo(self):
        # The bash script below returns a json dictionary with port names
        # as keys and values in the following format:
        # {
        #  "<port_name>": {
        #    "ifindex":<ifindex>,
        #    "port":<hex port>,
        #    "switch":<switch name>
        #    }
        # }
        script = \
        """
        echo '{' &&
        for i in $(find /sys/devices/virtual/net/ -maxdepth 2 -name 'brport');
        do
            IFACE=${i%/*}
            SWITCH=$(cd ${IFACE}/brport/bridge/ 2>/dev/null && pwd -P)
            echo -n '"'${IFACE##*/}'":{';
            echo -n '"ifindex":'$(cat ${IFACE}/ifindex)',';
            echo -n '"port":'$(printf "%d" $(cat ${IFACE}/brport/port_no) 2>/dev/null)',';
            echo    '"switch":"'${SWITCH##*/}'"},';
        done &&
        echo '}'
        """

        port_info = ''
        try:
            # This is not a good way to do this, but it is was fast to code
            cmd = 'ssh -o BatchMode=yes -o ConnectTimeout=1 %s %s' %\
                 (self._host, shellquote(script))
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stdout=subprocess.PIPE)
            port_info = p.communicate()[0]

            # Removing last ',' before parsing json
            port_info = port_info.replace('\n', '')[:-2] + '}'
            #sys.stderr.write('Port info: ' + str(port_info)+'\n')
        
            ports = json.loads(port_info)
            for port_name,port_info in ports.iteritems():
                sw = port_info['switch']
                if len(sw):
                    ifindex = port_info['ifindex']
                    port    = port_info['port']
                    if not self.has_key(sw):
                        self[sw] = {}
                    self[sw][ifindex] = {
                        'ifindex': ifindex,
                        'port': port,
                        'name': port_name
                    }
        except Exception, e:
            raise Exception(
                'Could not fetch OVS info. Are you sure you' +
                ' have passwordless access to host?')
        

    def updateInfo(self):
        self.clear()
        self.fetchPortInfo()
        
    def translate(self, sw, ifindex):
        """docstring for translate"""
        if self.has_key(sw):
            if self[sw].has_key(ifindex):
                return self[sw][ifindex]['port']
        return None
