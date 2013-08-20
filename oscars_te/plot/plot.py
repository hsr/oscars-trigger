#!/usr/bin/env python

# import os
# import sys
# import webapp
import oscars
import floodlight

# Floodlight controller url/ip address and port
def plot(controller = 'localhost:8080', oscarsdb = 'localhost'):
    errormsg = ''
    try:
        floodlight.update_topology_file(controller)
    except Exception, e:
        errormsg += str(e);
    try:
        oscars.update_active_circuits_file(oscarsdb)
    except Exception, e:
        errormsg += str(e);
    return errormsg
