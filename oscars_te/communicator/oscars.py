#!/usr/bin/python

import sys
import MySQLdb as my

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
    
SELECT_ACTIVE_CIRCUITS_SQL = \
"""SELECT r.id,p.seqNumber,urn FROM reservations AS r
    JOIN stdConstraints AS s ON s.reservationId = r.id
    JOIN pathElems as p ON p.pathId = s.pathId 
    WHERE r.status ='ACTIVE' and s.constraintType = 'reserved'
    ORDER BY p.pathId,seqNumber"""

def get_mysql_conn(host="infinerademo.es.net", port="3306", 
                   user="reader", passwd="reader", db="rm"):
    try:
        return my.connect(host=host, port=int(port), user=user, 
                          passwd=passwd, db=db)
    except Exception, e:
        raise Exception('Could not connect to OSCARS database at %s:%s\n' % (host,port))

def get_active_circuits(oscarsdb='localhost'):
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
    
    cursor.execute(SELECT_ACTIVE_CIRCUITS_SQL)
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
