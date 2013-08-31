// @import BaseTopology.js

var FloodlightTopology = BaseTopology;


FloodlightTopology.prototype.parseFloodlightTopology = function(file, callback) {
	var object = this;
    file = (typeof file === 'string' && file.length > 0) ?
    	 file : "/data/topology.json";


	 this.parseBaseTopology('', function () {
	 	var linkColor = '#0000AA';
	
	 	d3.json(file, function(topology) {
	 		topology.forEach(function(topologyLink) {
	 			var origin      = cleanDPID(topologyLink["src-switch"]),
	 				destination = cleanDPID(topologyLink["dst-switch"]),
	 				sport       = topologyLink["src-port"],
	 				dport       = topologyLink["dst-port"],
	 				links       = object.linksByOrigin[origin] || (object.linksByOrigin[origin] = []);

					console.log('adding new link');
	 			links.push({
	 				type: 'FLOODLIGHT',
	 				source: origin,
	 				sport:  sport,
	 				target: destination,
	 				tport:  dport,
	 				color:  linkColor
	 			});
		
	 			// // Manually add bi-directional links
	 			// links = object.linksByOrigin[destination] || (object.linksByOrigin[destination] = []);
	 			// sport = topologyLink["dst-port"];
	 			// dport = topologyLink["src-port"];
	 			// links.push({
	 			// 	type: 'FLOODLIGHT',
	 			// 	source: destination,
	 			// 	sport: sport,
	 			// 	target: origin,
	 			// 	tport: dport,
	 			// 	color: linkColor
	 			// });
	 		});
	 	});

	 	if (typeof callback === 'function') {
	 		callback();
	 	}
	 	
	});
}

