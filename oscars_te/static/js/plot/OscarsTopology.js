// @import BaseTopology.js

var OscarsTopology = FloodlightTopology;

OscarsTopology.prototype.parseOscarsTopology = function(controller, oscarsdb, callback) {
	var object = this;
    file = (typeof file === 'string' && file.length > 0) ?
    	 file : "/data/circuits.json";

	 object.parseFloodlightTopology(controller, function () {
		d3.json(oscarsdb, function(circuits) {
			
			var circuitHops  = {},
				circuitIDs   = {},
				previousHop  = '',
				previousID   = 0;

			circuits.forEach(function(circuitLink) {
				var id   = circuitLink.name,
				    hops = circuitHops[cleanDPID(id)] || (circuitHops[cleanDPID(id)] = '');
				hops += circuitLink.Dpid;
				circuitHops[cleanDPID(id)] = hops;
			});

			circuits.forEach(function(circuitLink) {
				var id    = circuitLink.name,
					hop   = circuitLink.Dpid,
					links = object.linksByOrigin[cleanDPID(hop)] || (object.linksByOrigin[cleanDPID(hop)] = []);

				// This assumes that all circuit links are sequential in the input file
				// i.e. no link from a circuit's set of links is mixed with other circuit's 
				// set of links in json
				if (previousID != id) {
					previousID  = id;
					previousHop = '';
				}

				if (previousHop != '') {
					if (cleanDPID(previousHop) != '0' && cleanDPID(hop) != '0') {
						links.push({
							id: id,
							type: 'CIRCUIT',
							source: cleanDPID(previousHop),
							target: cleanDPID(hop),
							color: '#' + colorFromString(circuitHops[id])
						});
					}
				}
				previousHop = hop
			});
			
		 	if (typeof callback === 'function') {
		 		callback();
		 	}
 		});
	});
}

