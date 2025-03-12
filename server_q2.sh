#!/bin/bash

SERVER_IP="192.168.95.143"  # Set your server's IP
PORT=8080                   # Port to use for iperf3 (note: iperf3 defaults to 5201 unless specified)
TCPDUMP_FILE="server_capture.pcap"

# Start iperf3 server in the background (remove -D since iperf3 doesn't support it)
echo "[*] Starting iperf3 server..."
iperf3 -s -p $PORT &  
IPERF_PID=$!

# Start packet capture
echo "[*] Capturing packets on $SERVER_IP:$PORT..."
sudo tcpdump -i wlo1 port $PORT -w $TCPDUMP_FILE &
TCPDUMP_PID=$!

# Wait for 250 seconds before stopping services
sleep 250

# Stop packet capture
echo "[*] Stopping packet capture..."
sudo kill $TCPDUMP_PID

# Stop iperf3 server using its PID
echo "[*] Stopping iperf3 server..."
kill $IPERF_PID

echo "[*] Server test complete. Packets saved in $TCPDUMP_FILE."
