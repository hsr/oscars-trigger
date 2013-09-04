function Plot(width, height) {
	if (typeof width != 'number' || typeof height != 'number') {
		width = 920;
		height = 500;
	}
	this.width = width;
	this.height = height;
}

Plot.prototype.init = function (callback) {
	var object = this;

	function zoomed(object) {
	  object.projection.translate(d3.event.translate).scale(d3.event.scale);
	  object.g.selectAll("path").attr("d", object.path);
	  
	  if (typeof object.draw === 'function') {
	  		  object.redraw();
	  }
	}

	this.projection = d3.geo.albersUsa()
	    .scale(1070)
	    .translate([this.width / 2, this.height / 2]);

	this.path = d3.geo.path()
	    .projection(this.projection);

	this.zoom = d3.behavior.zoom()
	    .translate(this.projection.translate())
	    .scale(this.projection.scale())
	    .scaleExtent([this.height, 8 * this.height])
	    .on("zoom", function() { zoomed(object) });

	this.svg = d3.select("#topology").append("svg")
	    .attr("width", this.width)
	    .attr("height", this.height);

	this.g = this.svg.append("g")
	    .call(this.zoom);
	
	this.g.append("rect")
	    .attr("class", "background")
	    .attr("width", this.width)
	    .attr("height", this.height);
	
	this.g.append("g")
  	     .attr("id", "states");
		  
	this.g.append("path")
		.attr("id", "borders");
		
	
	this.g.append("svg:g")
		.attr("id", "overlay");

	d3.select("#topology").data(this);
	
	if (typeof callback === 'function')
		callback();
}

Plot.prototype.usBackground = function(callback) {
	
	var object = this;
	
	d3.json("/static/data/us.json", function(error, us) {
	  d3.select("#states")
	    .selectAll("path")
	      .data(topojson.feature(us, us.objects.states).features)
	    .enter().append("path")
	      .attr("d", object.path);

	  d3.select("#borders")
	      .datum(topojson.mesh(us, us.objects.states, function(a, b) { return a !== b; }))
	      .attr("id", "state-borders")
	      .attr("d", object.path);
	});
	
	if (typeof callback === 'function')
		callback();
}
