#!/usr/bin/env python3
import subprocess
import csv
from collections import defaultdict
import matplotlib.pyplot as plt

DEBUG = True  # Set to True for debug output

def parse_flags(flags_str):
    """
    Parse the TCP flags from a string.
    Using int(flags_str, 0) allows auto-detection of hex (e.g., "0x0010").
    Returns a set of flag names.
    """
    try:
        flags_int = int(flags_str, 0)
    except ValueError:
        return set()
    flag_set = set()
    if flags_int & 0x02:
        flag_set.add('SYN')
    if flags_int & 0x10:
        flag_set.add('ACK')
    if flags_int & 0x01:
        flag_set.add('FIN')
    if flags_int & 0x04:
        flag_set.add('RST')
    return flag_set

def process_tcp_fields(filename):
    # Dictionary to store connection data: key = (src_ip, dst_ip, src_port, dst_port)
    # Value is a dict with keys 'start' and optionally 'end'
    connections = defaultdict(dict)
    
    with open(filename, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        # If you added a header, uncomment the next line:
        # next(reader, None)
        for row in reader:
            if DEBUG:
                print("DEBUG: row =", row)
            if len(row) < 6:
                if DEBUG:
                    print("DEBUG: Skipping row with insufficient fields:", row)
                continue
            time_epoch, src_ip, dst_ip, src_port, dst_port, flags_str = row
            flags = parse_flags(flags_str)
            if DEBUG:
                print("DEBUG: Parsed flags from", flags_str, "->", flags)
            conn_id = (src_ip, dst_ip, src_port, dst_port)
            try:
                time_epoch = float(time_epoch)
            except ValueError:
                if DEBUG:
                    print("DEBUG: Invalid time value:", time_epoch)
                continue

            # If this connection has not been seen before, record the first packet as start.
            if conn_id not in connections:
                connections[conn_id]['start'] = time_epoch
                if DEBUG:
                    print(f"DEBUG: Recorded start for {conn_id} at {time_epoch}")
            
            # Record termination events:
            # If a RST packet is seen and no end has been recorded, mark as end.
            if 'RST' in flags and 'end' not in connections[conn_id]:
                connections[conn_id]['end'] = time_epoch
                if DEBUG:
                    print(f"DEBUG: Recorded RST end for {conn_id} at {time_epoch}")
            
            # If both FIN and ACK are present, mark as termination.
            if 'FIN' in flags and 'ACK' in flags and 'end' not in connections[conn_id]:
                connections[conn_id]['end'] = time_epoch
                if DEBUG:
                    print(f"DEBUG: Recorded FIN-ACK end for {conn_id} at {time_epoch}")
    
    connection_data = []
    for conn_id, times in connections.items():
        if 'start' not in times:
            continue
        start = times['start']
        # If no termination is detected, assign a default duration of 100 seconds.
        end = times.get('end', start + 100)
        connection_data.append((start, end - start))
    
    return connection_data

def plot_connection_durations(connection_data):
    if not connection_data:
        print("No valid connections were found in the file.")
        return

    # Sort the data by connection start time.
    connection_data.sort(key=lambda x: x[0])
    start_times, durations = zip(*connection_data)

    plt.figure(figsize=(10,6))
    plt.scatter(start_times, durations, c='blue', label='Connection Duration')
    plt.xlabel('Connection Start Time (epoch seconds)')
    plt.ylabel('Connection Duration (seconds)')
    plt.title('Connection Duration vs. Connection Start Time')
    
    # Mark attack start and end (assuming experiment_start is the first recorded time)
    experiment_start = start_times[0]
    plt.axvline(x=experiment_start + 20, color='red', linestyle='--', label='Attack Start')
    plt.axvline(x=experiment_start + 120, color='green', linestyle='--', label='Attack End')
    
    plt.legend()
    plt.show()

def extract_tcp_fields(pcap_file, csv_file):
    # Use tshark to extract TCP fields from the PCAP file
    command = [
        'tshark', '-r', pcap_file, '-T', 'fields', '-e', 'frame.time_epoch',
        '-e', 'ip.src', '-e', 'ip.dst', '-e', 'tcp.srcport', '-e', 'tcp.dstport', '-e', 'tcp.flags',
        '-E', 'header=y', '-E', 'separator=,', '-E', 'quote=d', '-E', 'occurrence=f'
    ]
    with open(csv_file, 'w') as f:
        subprocess.run(command, stdout=f)

if __name__ == '__main__':
    pcap_file = 'attack.pcap'
    csv_file = 'tcp_fields.csv'
    
    extract_tcp_fields(pcap_file, csv_file)
    
    connection_data = process_tcp_fields(csv_file)
    print("Processed {} connections.".format(len(connection_data)))
    plot_connection_durations(connection_data)