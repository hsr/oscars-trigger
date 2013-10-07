#Simple WAN Traffic Engineering with OSCARS and SDN

In the summer of 2013, ESnet put efforts on the integration of [OSCARS](http://www.es.net/services/virtual-circuits-oscars/ OSCARS) and [Floodlight](http://www.projectfloodlight.org/floodlight/). In the SDN context, OSCARS is an application that controls the [ESnet](http://es.net/) 100G network and Floodlight is a SDN controller that communicates with network devices using [OpenFlow](http://www.openflow.org/).

This simple application demonstrates how one can monitor and optimize a circuit-managed network using OSCARS and SDN (see the end of this README for a install guide). 

The summer effort involved the development and extensions of multiple projects, including a new Path Setup Service for OSCARS, extensions to its internal classes and this web application.

Here is a complete list of the related projects:

####OSCARS - On-Demand Secure Circuits and Advance Reservation System

ESnet's On-Demand Secure Circuits and Advance Reservation System (OSCARS) provides multi-domain, high-bandwidth virtual circuits that guarantee end-to-end network data transfer performance. Originally a research concept, OSCARS has grown into a robust production service. Currently OSCARS virtual circuits carry fifty percent of ESnet’s annual 60 petabytes of traffic.[^1]

[^1]: Source: http://www.es.net/services/virtual-circuits-oscars/ 

Check the [code on github](http://github.com/hsr/oscars)

####OSCARS SDNPSS - Path Setup Service interface to SDN Controllers

At the edge of the OSCARS Reservation Engine is the Path Setup Subsystem (PSS), which is responsible for the interface between network devices and OSCARS. This project implements the interface between OSCARS and Floodlight, the SDN controller that is currently supported by OSCARS.

Check the [code on github](http://github.com/hsr/oscars-sdnpss)

####OSCARS Listener - Requesting circuits using JSON

This project implements a simple HTTP service that translates JSON circuit reservation requests to the OSCARS API.

Check the [code on github](http://github.com/hsr/oscars-listener)

#### OSCARS Trigger - Simple Traffic Engineering for OSCARS

The OSCARS Trigger (this application) interfaces with OSCARS and the SDN controller to provide multiple features, such as multilayer network visualization, OpenFlow monitoring and simple traffic offloading.

Here is an screenshot of the web interface:
![alt text](https://raw.github.com/hsr/oscars-trigger/master/screenshot.png "OSCARS Trigger Web interface")
**Legend:**

![alt text](https://raw.github.com/hsr/oscars-trigger/master/legend.png "Legend"")


To install and run the application, follow these steps:

    # clone the repository
    git clone http://github.com/hsr/oscars-trigger
    cd oscars-trigger
    
    # install dependencies
    sudo pip install -r requirements.txt
    sudo apt-get -y install python-mysqldb
    
    # create the database
    python ./db_create.py
    
    # run the application
    python ./run.py --controller=<Floodlight controller IP> \
                    --oscars=<OSCARS server IP>

Check the [code on github](http://github.com/hsr/oscars-trigger)
