parseFloodlightTopology("/static/data/demoTopology.json", function() {
	parseFloodlightTopology("/data/topology.json", function () { 
		drawFloodlightTopology("/static/data/infinerademoLocationMap.csv", function() {
			drawFloodlightCircuits();
		})
	})
});