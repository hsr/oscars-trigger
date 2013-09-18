#!/usr/bin/python

import sys
import MySQLdb as my
from config import OSCARS_MYSQL_USERNAME, OSCARS_MYSQL_PASSWORD

err = ''

URN_DOMAIN = 0
URN_NODE   = 1
URN_PORT   = 2
URN_LINK   = 3

# SELECT_CIRCUITS_SQL = "SELECT id,globalReservationId FROM reservations WHERE status = 'ACTIVE'"
# SELECT_CIRCUITPATH_SQL = "SELECT urn FROM pathElems WHERE pathId = '%d' ORDER BY seqNumber";

# SELECT_ACTIVE_CIRCUITS_SQL = \
# """SELECT reservations.id,seqNumber,urn FROM pathElems
#     JOIN reservations ON pathElems.pathId = reservations.id
#     WHERE reservations.status = 'ACTIVE'
#     ORDER BY pathId,seqNumber"""
    
SELECT_CIRCUITS_SQL = \
"""SELECT r.id,p.seqNumber,urn,s.bandwidth FROM reservations AS r
    JOIN stdConstraints AS s ON s.reservationId = r.id
    JOIN pathElems as p ON p.pathId = s.pathId 
    WHERE r.status ='%s' and s.constraintType = 'reserved'
    ORDER BY p.pathId,seqNumber"""

def get_mysql_conn(host="infinerademo.es.net", port="3306"):
    user = OSCARS_MYSQL_USERNAME
    passwd = OSCARS_MYSQL_PASSWORD
    try:
        return my.connect(host=host, port=int(port), user=user, 
                          passwd=passwd, db="rm")
    except Exception, e:
        raise Exception('Could not connect to OSCARS database at %s:%s\n' % \
             (host,port))

def get_circuits_by_status(oscarsdb='localhost', status='ACTIVE'):
    """
    Returns a dict with circuit info in the following format:
    
    {
        <id>: {
            'bandwidth': <bandwidth>
            'hops': {
                0: {'node': <node>, 'port': <port>}
                1: {'node': <node>, 'port': <port>}
                ...
            }
        }
        <id>: ...
        ...
    }
    
    """
    host,port = (oscarsdb,3306)
    if len(host.split(':')) > 1:
        host,port = host.split(':')
        
    conn = get_mysql_conn(host=host, port=port);
    if not conn:
        raise Exception('Could not open mysql connection')
    
    circuits = {}
    cursor = conn.cursor()
    cursor.execute(SELECT_CIRCUITS_SQL % status)
    
    for hop in cursor.fetchall():
        id,seq,urn = (hop[0],hop[1],urn_split(hop[2]))
        
    
        if not circuits.has_key(id):
            circuits[id] = {'bandwidth': hop[3], 'hops':{}}
    
        circuits[id]['hops'][int(seq)] = {
            'node': urn[URN_NODE],
            'port': urn[URN_PORT],
        }
    
    return circuits

def get_active_circuits(oscarsdb='localhost', status='ACTIVE'):
    """
    Query the mysql oscars db for circuits. 
    Returns json-formatted objects describing circuit hops, one per line.
    Sample output:
    
    {"name":"testdomain-1-12", "Dpid":"00.00.00.00.00.00.00.04"}
    {"name":"testdomain-1-12", "Dpid":"11.11.00.00.00.00.00.05"}
    {"name":"testdomain-1-12", "Dpid":"11.11.00.00.00.00.00.06"}
    {"name":"testdomain-1-12", "Dpid":"00.00.00.00.00.00.00.07"}
    """
    host,port = (oscarsdb,3306)
    if len(host.split(':')) > 1:
        host,port = host.split(':')
    
    
    conn = get_mysql_conn(host=host, port=port);
    if not conn:
        return None;
    
    cursor = conn.cursor()
    # for circuit in cursor.fetchall(SELECT_CIRCUIT_SQL):
    #     path = cursor.fetchall(SELECT_CIRCUIT_SQL)
    circuit_id   = None
    nodes        = []
    circuitsById = {}
    
    cursor.execute(SELECT_CIRCUITS_SQL % status)
    for hop in cursor.fetchall():
        id,seq,urn = (hop[0],hop[1],urn_split(hop[2]))

        urn[URN_NODE] = urn[URN_NODE].replace('.', ':')
                    
        if circuit_id != id:
            if circuit_id:
                if not circuitsById.has_key(circuit_id):
                    circuitsById[circuit_id] = nodes
                #print '%s:' % circuit_id, nodes
            circuit_id = id
            nodes      = []
        
        if urn[URN_NODE] not in nodes:
            nodes += [urn[URN_NODE]]
        
        #print id,seq,urn

    if not circuitsById.has_key(circuit_id):
        circuitsById[circuit_id] = nodes

    if len(circuitsById.values()):
        ret = ''
        for id,hops in circuitsById.items():
            for hop in hops:
                ret += '{"name": "%s", "Dpid": "%s"}\n' % (id, hop);
        return ret;
        
    raise Exception('No circuits')
    
    

def urn_split(urn):
    return [value.split('=')[1] for value in urn.split(':')[3:]]
    
def update_active_circuits_file(oscarsdb='localhost'):
    try:
        circuits = get_active_circuits(oscarsdb);
    except Exception, e:
        raise Exception(e)

    circuits_filename = 'oscars_te/data/circuits.json'
    try:
        circuits_file = open(circuits_filename, 'w');
    except Exception, e:
        raise Exception('Could not open circuits output file. ');

    # for id,hops in circuitsById.items():
    #     for hop in hops:
    #         circuits_file.write('{"name": "%s", "Dpid": "%s"}\n' % (id, hop));
    circuits_file.write(circuits);
    
    circuits_file.close()
