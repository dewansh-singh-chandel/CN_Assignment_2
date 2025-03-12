import os
import re
import glob
import matplotlib.pyplot as plt

# Directory containing the log files
log_dir = r'/home/dewansh/Documents/CN_Assignment/Assignement_2/logs_q1_B'
# Directory to save the graphs
output_dir = r'/home/dewansh/Documents/CN_Assignment/Assignement_2/cs331-cwnd'

# Create the output directory if it doesn't exist
os.makedirs(output_dir, exist_ok=True)

# Pattern to match log files excluding those with 'reno' in their names
log_files_pattern = os.path.join(log_dir, '*[!reno]*.log')

# Function to parse the log file and extract time and cwnd values
def parse_log_file(file_path):
    time_cwnd = []
    with open(file_path, 'r') as file:
        for line in file:
            match = re.search(r'\[\s*\d+\]\s+(\d+\.\d+|\d+)-(\d+\.\d+|\d+)\s+sec\s+(\d+\.\d+|\d+)\s+(KBytes|MBytes)\s+(\d+\.\d+|\d+)\s+(bits/sec|Kbits/sec|Mbits/sec)\s+\d+\s+(\d+\.\d+|\d+)\s+(KBytes|MBytes)', line)
            if match:
                start_time = float(match.group(1))
                end_time = float(match.group(2))
                transfer_size = float(match.group(3))
                transfer_unit = match.group(4)
                cwnd = float(match.group(7))
                cwnd_unit = match.group(8)
                if transfer_unit == 'MBytes':
                    transfer_size *= 1024  # Convert MBytes to KBytes
                if cwnd_unit == 'MBytes':
                    cwnd *= 1024  # Convert MBytes to KBytes
                time_cwnd.append((end_time, cwnd))
    return time_cwnd

# Collect data from each matching log file and plot the graph
for log_file in glob.glob(log_files_pattern):
    time_cwnd = parse_log_file(log_file)
    if time_cwnd:
        # Sort data by time
        time_cwnd.sort()
        # Separate time and cwnd values
        times, cwnds = zip(*time_cwnd)
        # Plotting the graph
        plt.figure(figsize=(10, 6))
        plt.plot(times, cwnds, marker='o', linestyle='-', color='#254e8a', markersize=4)
        plt.xlabel('Time (seconds)')
        plt.ylabel('CWND (KBytes)')
        plt.title(f'CWND vs Time')
        plt.grid(True)
        # Save the graph
        output_file = os.path.join(output_dir, f'{os.path.basename(log_file)}.png')
        plt.savefig(output_file)
        plt.close()