drawUSBackground();
parseFloodlightTopology("/static/data/topology/base.json", function() {
	parseFloodlightTopology("/data/topology.json", function () { 
		drawFloodlightTopology("/static/data/coordinates/base.csv", function() {
			drawFloodlightCircuits();
		})
	})
});