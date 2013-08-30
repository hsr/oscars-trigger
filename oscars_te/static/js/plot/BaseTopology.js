// @import Plot.js

var BaseTopology = Plot;

BaseTopology.prototype.cleanup = function () {
	this.deviceByDPID     = {};
	this.DPIDByDevice     = {};
	this.locationByDevice = {};
	this.circuitLinksById = {};
	this.positions        = [];	
}

BaseTopology.prototype.initBaseTopology = function() {
	var object = this;
	
	this.positions        = [];	
	this.locationByDevice = {};
	this.linksByOrigin    = {};
	this.countByDevice    = {};
	this.devices          = [];
	
	this.linkArc = d3.geo.greatArc()
		.source(function(d) {
		var location = [0,0];
		
		switch (d.type) {
		case 'BASE':
			location = this.locationByDevice[d.source];
			break;
		case 'FLOODLIGHT':
			location = [this.locationByDevice[d.source][0] + .2, this.locationByDevice[d.source][1] + .2];
			break;
		case 'FLOODLIGHT':
			location = [this.locationByDevice[d.source][0] + .4, this.locationByDevice[d.source][1] + .4];
			break;
		}
		return location;

	})
		.target(function(d) {
		var location = [0,0];
		
		switch (d.type) {
		case 'BASE':
			location = this.locationByDevice[d.target];
			break;
		case 'FLOODLIGHT':
			location = [this.locationByDevice[d.target][0] + .2, this.locationByDevice[d.target][1] + .2];
			break;
		case 'CIRCUIT':
			location = [this.locationByDevice[d.target][0] + .4, this.locationByDevice[d.target][1] + .4];
			break;
		}
		return location;
	});
}

BaseTopology.prototype.parseBaseTopology = function(file, callback) {
	var object = this;
    file = (typeof file === 'string') ?
    	 file : "/static/data/topology/base.json";

	var linkColor = '#000000';
	
	d3.json(file, function(topology) {
		topology.forEach(function(topologyLink) {
			var origin      = cleanDPID(topologyLink["src-switch"]),
				destination = cleanDPID(topologyLink["dst-switch"]),
				sport       = topologyLink["src-port"],
				dport       = topologyLink["dst-port"],
				links       = object.linksByOrigin[origin] || (object.linksByOrigin[origin] = []);

			links.push({
				type: 'BASE',
				source: origin,
				sport: sport,
				target: destination,
				tport: dport,
				color: linkColor
			});
		
			// Manually add bi-directional links
			links = object.linksByOrigin[destination] || (object.linksByOrigin[destination] = []);
			sport = topologyLink["dst-port"];
			dport = topologyLink["src-port"];
			links.push({
				type: 'BASE',
				source: destination,
				sport: sport,
				target: origin,
				tport: dport,
				color: linkColor
			});

			object.countByDevice[origin] = object.countByDevice[destination] = 2;
		});
	});

	if (typeof callback === 'function') {
		callback();
	}
};


BaseTopology.prototype.redraw = function(callback) {
	var object = this;
	var overlay = d3.select("#overlay");

	d3.selectAll("#overlay g").remove();
	this.cleanup();

	this.cells = overlay.append("svg:g")
	    .attr("id", "cells")
		//.attr("class", "voronoi")
		;
	
	this.circles = overlay.append("svg:g")
	    .attr("id", "circles");

	this.circuits = overlay.append("svg:g")
	    .attr("id", "circuits");
	
	// update
	var devices = this.devices.filter(function(device) {
		var location = [+device.longitude, + device.latitude];

		object.positions.push(object.projection(location));

		// do not calculate projection for locationByDevice, 
		// it will be calculated later with object.path()
		object.locationByDevice[device.dpid] = location;
		return true;
	});	

	devices.forEach(function () {
		
		// Compute the Voronoi diagram of devices' projected positions.
		object.polygons = d3.geom.voronoi(object.positions);
		
		var g = object.cells.selectAll("g")
			.data(devices)
			.enter()
			.append("svg:g");

		// Adding voronoi cells
		g.append("svg:path")
			.attr("class", "cell")
			.attr("d", function(d, i) {	return "M" + object.polygons[i].join("L") + "Z"; })
			.on("mouseover", function(d, i) {
				var desc = "Device " + d.dpid + ",\n"
				var links = 'Links (port->node): '
				object.linksByOrigin[d.dpid].forEach(function(l) {
					links += l.sport + '->' + l.target + ','
				});
				d3.select("#deviceinfo")
					.text(desc + links);
			});

		// Draw links using the linkArc object defined before
		g.selectAll("path.arc")
			.data(function(d) {	return object.linksByOrigin[d.dpid] || [];	})
			.enter()
			.append("svg:path")
			.attr("class", "arc")
			.style("stroke", function(d) { return d.color; })
			.style("stroke-dasharray", function(d) { if (d.type == 'FLLINK') {return '5,7';} return '0'; })
			.attr("d", function(d) { 
				//console.log(object.linkArc(d));
				return object.path(object.linkArc(d)); });

		// Draw circles
		object.circles.selectAll("circle")
			.data(devices).enter().append("svg:circle")
			.attr("cx", function(d, i) { return object.positions[i][0]; })
			.attr("cy", function(d, i) { return object.positions[i][1]; })
			.attr("r", function(d, i) {	return object.countByDevice[d.dpid] * 4; })
			.style("fill", function(d, i) {
				if (devices[i].type == 1) {
					return "red";
				}
				return "blue";
			})
			.sort(function(a, b) { return object.countByDevice[b.dpid] - object.countByDevice[a.dpid]; });

		// Add labels
		g.append("svg:text")
			.attr("x", function(d, i) { return object.positions[i][0] + 5; })
			.attr("y", function(d, i) {	return object.positions[i][1];	})
			.attr("dy", ".2em")
			.attr("class", "label")
			.attr("id", function(d) { return 'netdev' + d.dpid; })
			.text(function(d) { return d.dpid; });
	
	
		if (typeof callback !== 'undefined') {
			callback();
		}
	});	
}


BaseTopology.prototype.draw = function(file, callback) {
	var object = this;
	
	file = typeof file === 'string' ?
		file : "/static/data/coordinates/base.csv";


	d3.csv(file, function(devices) {
		
		// Only consider devices with at least one link.
		devices = devices.filter(function(device) {
			if (object.countByDevice[device.dpid]) {
				var location = [+device.longitude, + device.latitude];
				object.locationByDevice[device.dpid] = location;
				object.positions.push(object.projection(location));
				return true;
			}
		});
		
		object.devices = devices;
		object.redraw();
	});
}

