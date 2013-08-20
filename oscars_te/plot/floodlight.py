from flask import url_for
import urllib2
import socket
import sys
import os



def get_topology(controller='localhost'):
    """Fetches topology from given controller. Returns the json fetched topology.
    An Exception is raised in case of failures."""
    host,port = (controller,8080)
    if len(host.split(':')) > 1:
        host,port = host.split(':')

    try:
        host = socket.gethostbyname(host)
    except Exception:
        raise Exception('Could not resolve controller hostname. ')

    url = "http://%s:%s/wm/topology/links/json" % (host,port)
    try:
        response = urllib2.urlopen(url, timeout=1).read();
        if len(response):
            return response
    except Exception, e:
        raise Exception('Could not fetch topology: %s. ' % e.message)
    raise Exception('No response from controller.\n')
    
def update_topology_file(controller):
    """Fetches and updates the topology file. An Exception is raised in case of failures."""
    try:
        floodlightTopology = get_topology(controller)
    except Exception, e:
        raise e

    try:
        topology_file = open('oscars_te/static/data/topology.json', 'w');
        topology_file.write(floodlightTopology)
        topology_file.close()
    except Exception, e:
        raise Exception('Could not write floodlight topology. ')

