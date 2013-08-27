import oscars
import floodlight

# Floodlight controller url/ip address and port
def plot(controller = 'localhost:8080', oscarsdb = 'localhost'):
    errormsg = ''
    if controller != 'skip':
        try:
            floodlight.update_topology_file(controller)
        except Exception, e:
            errormsg += str(e);
    try:
        oscars.update_active_circuits_file(oscarsdb)
    except Exception, e:
        errormsg += str(e);
    return errormsg
