#!/usr/bin/env python3
"""
Custom topology and TCP congestion control experiments using Mininet and iperf3.

Topology for experiments (a) and (b):
  - Hosts h1 and h2 are connected to switch s1.
  - Host h3 is connected to switch s2.
  - Hosts h4 and h5 are connected to switch s3.
  - Hosts h6 and h7 (TCP server) are connected to switch s4.
  - Switches are connected in a chain: s1 -- s2 -- s3 -- s4.

Experiment (a):
  - Run iperf3 server on h7 and client on h1.
  - Command: iperf3 -c <server_ip> -p 5201 -b 10M -P 10 -t 150 -C <cc_scheme>
  - Optional link loss can be applied on h1’s interface.

Experiment (b): Staggered flows:
  - h1: starts at T=0 sec for 150 sec
  - h3: starts at T=15 sec for 120 sec
  - h4: starts at T=30 sec for 90 sec
  - Server always on h7.

Experiment (c):
  - Bandwidth configuration experiments with TCLink.
  - Depending on the scenario (passed via --scenario):
      * scenario "1": Add direct link between s2 and s4; run client on h3.
      * scenario "2a": Add direct link between s1 and s4; run clients on h1 and h2.
      * scenario "2b": Add direct link between s1 and s4; run clients on h1 and h3.
      * scenario "2c": Add direct link between s1 and s4; run clients on h1, h3 and h4.

Experiment (d):
  - Same as experiment (c) but with the link between s2 and s3 configured with loss.

Usage examples:
  sudo python3 setup.py --option a --cc cubic --loss 0
  sudo python3 setup.py --option b --cc cubic
  sudo python3 setup.py --option c --cc cubic --scenario 2a --loss 0
  sudo python3 setup.py --option d --cc cubic --scenario 2a --loss 1
"""

import argparse
import time
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import OVSController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink

# Base port number for iperf3 tests
BASE_PORT = 8080

class MyTopo(Topo):
    def __init__(self, bw_config=False, loss_param=0, **opts):
        """
        bw_config: if True, configure inter-switch links with bandwidth limits.
        loss_param: if > 0 and bw_config is True, apply this loss percentage on the s2-s3 link.
        """
        self.bw_config = bw_config
        self.loss_param = loss_param
        Topo.__init__(self, **opts)

    def build(self):

        # Add switches.
        s1 = self.addSwitch('s1')
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')

        # Add hosts.
        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')
        h5 = self.addHost('h5')
        h6 = self.addHost('h6')
        h7 = self.addHost('h7')  # TCP server

        # Connect hosts to switches.
        self.addLink(h1, s1)
        self.addLink(h2, s1)
        self.addLink(h3, s2)
        self.addLink(h4, s3)
        self.addLink(h5, s3)
        self.addLink(h6, s4)
        self.addLink(h7, s4)

        # Connect switches.
        if self.bw_config:
            self.addLink(s1, s2, bw=100)
            if self.loss_param > 0:
                self.addLink(s2, s3, bw=50, loss=self.loss_param)
            else:
                self.addLink(s2, s3, bw=50)
            self.addLink(s3, s4, bw=100)
        else:
            self.addLink(s1, s2)
            self.addLink(s2, s3)
            self.addLink(s3, s4)

# Allow loading via "sudo mn --custom setup.py --topo mytopo"
topos = { 'mytopo': (lambda: MyTopo()) }

def experiment_a(net, cc_scheme, link_loss):
    """
    Experiment (a): Single flow from h1 to h7.
    """
    h1 = net.get('h1')
    h7 = net.get('h7')
    serverIP = h7.IP()

    if link_loss > 0:
        print("Applying {}% packet loss on h1-eth0".format(link_loss))
        h1.cmd("tc qdisc add dev h1-eth0 root netem loss {}%".format(link_loss))
    
    print("Starting iperf3 server on h7 (port {})...".format(BASE_PORT))
    h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
    time.sleep(2)
    
    input("Press Enter to start the iperf3 client on h1...")

    cmd = ("iperf3 -c {} -p {} -b 10M -P 10 -t 150 -C {} "
           "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
    print("Starting iperf3 client on h1 with scheme '{}' on port {}".format(cc_scheme, BASE_PORT))
    h1.cmd(cmd)
    time.sleep(155)
    
    if link_loss > 0:
        h1.cmd("tc qdisc del dev h1-eth0 root netem")
    print("Experiment (a) completed. Check /tmp/iperf_h1.log for results.")

def experiment_b(net, cc_scheme):
    """
    Experiment (b): Staggered flows on h1, h3, and h4.
      - h1: starts at 0 sec, duration 150 sec.
      - h3: starts at 15 sec, duration 120 sec.
      - h4: starts at 30 sec, duration 90 sec.
    """
    h1 = net.get('h1')
    h3 = net.get('h3')
    h4 = net.get('h4')
    h7 = net.get('h7')
    serverIP = h7.IP()

    print("Starting iperf3 servers on h7 on ports {} to {}...".format(BASE_PORT, BASE_PORT+2))
    h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
    h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+1))
    h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+2))
    time.sleep(2)
    
    input("Press Enter to start the iperf3 clients on h1, h3, and h4...")

    # h1 starts at T=0 sec, duration 150 sec on port BASE_PORT.
    cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 150 -C {} "
            "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
    print("Starting iperf3 client on h1 with '{}' on port {}".format(cc_scheme, BASE_PORT))
    h1.cmd(cmd1)
    time.sleep(15)

    # h3 starts at T=15 sec, duration 120 sec on port BASE_PORT+1.
    cmd3 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 120 -C {} "
            "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
    print("Starting iperf3 client on h3 with '{}' on port {}".format(cc_scheme, BASE_PORT+1))
    h3.cmd(cmd3)
    time.sleep(15)

    # h4 starts at T=30 sec, duration 90 sec on port BASE_PORT+2.
    cmd4 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 90 -C {} "
            "> /tmp/iperf_h4.log 2>&1 &").format(serverIP, BASE_PORT+2, cc_scheme)
    print("Starting iperf3 client on h4 with '{}' on port {}".format(cc_scheme, BASE_PORT+2))
    h4.cmd(cmd4)
    time.sleep(150)

    print("Experiment (b) completed. Check /tmp/iperf_h1.log, /tmp/iperf_h3.log, and /tmp/iperf_h4.log.")

def experiment_c(scenario, net, cc_scheme):
    """
    Experiment (c): Bandwidth configuration experiments without link loss.
    
    Scenarios (choose via --scenario):
      - "1": Add direct link between s2 and s4; run client on h3.
      - "2a": Add direct link between s1 and s4; run clients on h1 and h2.
      - "2b": Add direct link between s1 and s4; run clients on h1 and h3.
      - "2c": Add direct link between s1 and s4; run clients on h1, h3 and h4.
    """
    print("Experiment (c), scenario '{}'".format(scenario))
    h7 = net.get('h7')
    serverIP = h7.IP()

    # Start iperf3 server(s) on h7 based on scenario.
    if scenario == '1':
        print("Starting iperf3 server on h7 (port {})...".format(BASE_PORT))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
    elif scenario in ['2a', '2b']:
        print("Starting iperf3 servers on h7 on ports {} and {}...".format(BASE_PORT, BASE_PORT+1))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+1))
    elif scenario == '2c':
        print("Starting iperf3 servers on h7 on ports {} to {}...".format(BASE_PORT, BASE_PORT+2))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+1))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+2))
    else:
        print("Invalid scenario for experiment (c).")
        return

    time.sleep(2)
    
    if scenario == '1':
        s2 = net.get('s2')
        s4 = net.get('s4')
        print("Scenario 1: Adding direct link between s2 and s4 (bw=100Mbps).")
        net.addLink(s2, s4, bw=100)
        h3 = net.get('h3')

        input("Press Enter to start the iperf3 client on h3...")

        cmd = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
               "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        print("Starting iperf3 client on h3 with '{}' on port {}".format(cc_scheme, BASE_PORT))
        h3.cmd(cmd)
        time.sleep(35)
    
    elif scenario == '2a':
        s1 = net.get('s1')
        s4 = net.get('s4')
        print("Scenario 2a: Adding direct link between s1 and s4 (bw=100Mbps).")
        net.addLink(s1, s4, bw=100)
        h1 = net.get('h1')
        h2 = net.get('h2')

        input("Press Enter to start the iperf3 clients on h1 and h2...")

        cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        cmd2 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h2.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
        print("Starting iperf3 clients on h1 (port {}) and h2 (port {}) with '{}'".format(BASE_PORT, BASE_PORT+1, cc_scheme))
        h1.cmd(cmd1)
        h2.cmd(cmd2)
    
    elif scenario == '2b':
        s1 = net.get('s1')
        s4 = net.get('s4')
        print("Scenario 2b: Adding direct link between s1 and s4 (bw=100Mbps).")
        net.addLink(s1, s4, bw=100)
        h1 = net.get('h1')
        h3 = net.get('h3')

        input("Press Enter to start the iperf3 clients on h1 and h3...")

        cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        cmd3 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
        print("Starting iperf3 clients on h1 (port {}) and h3 (port {}) with '{}'".format(BASE_PORT, BASE_PORT+1, cc_scheme))
        h1.cmd(cmd1)
        h3.cmd(cmd3)
    
    elif scenario == '2c':
        s1 = net.get('s1')
        s4 = net.get('s4')
        print("Scenario 2c: Adding direct link between s1 and s4 (bw=100Mbps).")
        net.addLink(s1, s4, bw=100)
        h1 = net.get('h1')
        h3 = net.get('h3')
        h4 = net.get('h4')

        input("Press Enter to start the iperf3 clients on h1, h3, and h4...")

        cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        cmd3 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
        cmd4 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h4.log 2>&1 &").format(serverIP, BASE_PORT+2, cc_scheme)
        print("Starting iperf3 clients on h1 (port {}), h3 (port {}), and h4 (port {}) with '{}'".format(BASE_PORT, BASE_PORT+1, BASE_PORT+2, cc_scheme))
        h1.cmd(cmd1)
        h3.cmd(cmd3)
        h4.cmd(cmd4)
    time.sleep(35)
    print("Experiment (c) completed. Check the corresponding log files for results.")

def experiment_d(scenario, net, cc_scheme):
    """
    Experiment (d): Same as experiment (c) but with the link between s2 and s3 configured with loss.
    """
    print("Experiment (d), scenario '{}' with link loss on s2-s3".format(scenario))
    h7 = net.get('h7')
    serverIP = h7.IP()

    # Start iperf3 server(s) on h7 based on scenario.
    if scenario == '1':
        print("Starting iperf3 server on h7 (port {})...".format(BASE_PORT))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
    elif scenario in ['2a', '2b']:
        print("Starting iperf3 servers on h7 on ports {} and {}...".format(BASE_PORT, BASE_PORT+1))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+1))
    elif scenario == '2c':
        print("Starting iperf3 servers on h7 on ports {} to {}...".format(BASE_PORT, BASE_PORT+2))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+1))
        h7.cmd("iperf3 -s -p {} -D".format(BASE_PORT+2))
    else:
        print("Invalid scenario for experiment (d).")
        return

    time.sleep(2)
    
    if scenario == '1':
        s2 = net.get('s2')
        s4 = net.get('s4')
        print("Scenario 1: Adding direct link between s2 and s4 (bw=100Mbps).")
        net.addLink(s2, s4, bw=100)
        h3 = net.get('h3')

        input("Press Enter to start the iperf3 client on h3...")

        cmd = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
               "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        print("Starting iperf3 client on h3 with '{}' on port {}".format(cc_scheme, BASE_PORT))
        h3.cmd(cmd)
        time.sleep(35)
    
    elif scenario == '2a':
        s1 = net.get('s1')
        s4 = net.get('s4')
        print("Scenario 2a: Adding direct link between s1 and s4 (bw=100Mbps).")
        net.addLink(s1, s4, bw=100)
        h1 = net.get('h1')
        h2 = net.get('h2')

        input("Press Enter to start the iperf3 clients on h1 and h2...")

        cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        cmd2 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h2.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
        print("Starting iperf3 clients on h1 (port {}) and h2 (port {}) with '{}'".format(BASE_PORT, BASE_PORT+1, cc_scheme))
        h1.cmd(cmd1)
        h2.cmd(cmd2)
    
    elif scenario == '2b':
        s1 = net.get('s1')
        s4 = net.get('s4')
        print("Scenario 2b: Adding direct link between s1 and s4 (bw=100Mbps).")
        net.addLink(s1, s4, bw=100)
        h1 = net.get('h1')
        h3 = net.get('h3')

        input("Press Enter to start the iperf3 clients on h1 and h3...")

        cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        cmd3 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
        print("Starting iperf3 clients on h1 (port {}) and h3 (port {}) with '{}'".format(BASE_PORT, BASE_PORT+1, cc_scheme))
        h1.cmd(cmd1)
        h3.cmd(cmd3)
    
    elif scenario == '2c':
        s1 = net.get('s1')
        s4 = net.get('s4')
        print("Scenario 2c: Adding direct link between s1 and s4 (bw=100Mbps).")
        net.addLink(s1, s4, bw=100)
        h1 = net.get('h1')
        h3 = net.get('h3')
        h4 = net.get('h4')

        input("Press Enter to start the iperf3 clients on h1, h3, and h4...")

        cmd1 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h1.log 2>&1 &").format(serverIP, BASE_PORT, cc_scheme)
        cmd3 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h3.log 2>&1 &").format(serverIP, BASE_PORT+1, cc_scheme)
        cmd4 = ("iperf3 -c {} -p {} -b 10M -P 10 -t 30 -C {} "
                "> /tmp/iperf_h4.log 2>&1 &").format(serverIP, BASE_PORT+2, cc_scheme)
        print("Starting iperf3 clients on h1 (port {}), h3 (port {}), and h4 (port {}) with '{}'".format(BASE_PORT, BASE_PORT+1, BASE_PORT+2, cc_scheme))
        h1.cmd(cmd1)
        h3.cmd(cmd3)
        h4.cmd(cmd4)
    time.sleep(35)
    print("Experiment (d) completed. Check the corresponding log files for results.")

if __name__ == '__main__':
    setLogLevel('info')
    
    parser = argparse.ArgumentParser(description="Mininet TCP Congestion Control Experiment")
    parser.add_argument("--option", type=str, default="null",
                        help="Experiment option: a, b, c, or d")
    parser.add_argument("--cc", type=str, default="cubic",
                        help="TCP congestion control scheme")
    parser.add_argument("--loss", type=float, default=0.0,
                        help="Link loss percentage (for experiment a and for experiment d on link s2-s3)")
    parser.add_argument("--scenario", type=str, default="",
                        help="For experiments c and d, specify scenario: 1, 2a, 2b, or 2c")
    args = parser.parse_args()
    
    if args.option.lower() == 'null':
        net = Mininet(topo=MyTopo(bw_config=False), controller=OVSController)
    elif args.option.lower() in ['a', 'b']:
        net = Mininet(topo=MyTopo(bw_config=False), controller=OVSController)
    elif args.option.lower() == 'c':
        net = Mininet(topo=MyTopo(bw_config=True), controller=OVSController, link=TCLink)
    elif args.option.lower() == 'd':
        net = Mininet(topo=MyTopo(bw_config=True, loss_param=args.loss), controller=OVSController, link=TCLink)
    else:
        print("Invalid option specified. Use --option a, b, c, or d.")
        exit(1)
    
    net.start()
    
    if args.option.lower() == 'null':
        pass
    elif args.option.lower() == 'a':
        experiment_a(net, cc_scheme=args.cc, link_loss=args.loss)
    elif args.option.lower() == 'b':
        experiment_b(net, cc_scheme=args.cc)
    elif args.option.lower() == 'c':
        experiment_c(args.scenario, net, cc_scheme=args.cc)
    elif args.option.lower() == 'd':
        experiment_d(args.scenario, net, cc_scheme=args.cc)
    
    CLI(net)
    net.stop()

