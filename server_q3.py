import socket
import argparse

def start_server(host='0.0.0.0', port=8080, disable_nagle=False, disable_delayed_ack=False):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"Server started at {host}:{port}, waiting for connections...")
    print(f"Nagle Algorithm Disabled: {disable_nagle}")
    print(f"Delayed ACK Disabled: {disable_delayed_ack}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Connection established with {client_address}")

        # Disable Nagle (TCP_NODELAY)
        if disable_nagle:
            client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"Nagle's algorithm disabled for connection with {client_address}")

        # Disable Delayed ACK (if supported)
        if disable_delayed_ack:
            try:
                TCP_QUICKACK = getattr(socket, 'TCP_QUICKACK', None)
                if TCP_QUICKACK is not None:
                    client_socket.setsockopt(socket.IPPROTO_TCP, TCP_QUICKACK, 1)
                    print(f"Delayed ACK disabled (TCP_QUICKACK set) for connection with {client_address}")
                else:
                    print("TCP_QUICKACK not supported on this platform - cannot disable delayed ACK.")
            except Exception as e:
                print(f"Failed to set TCP_QUICKACK: {e}")

        received_bytes = 0

        try:
            while True:
                chunk = client_socket.recv(1024)
                if not chunk:
                    break
                received_bytes += len(chunk)
                print(f"Received {len(chunk)} bytes, Total received so far: {received_bytes} bytes")

            print(f"Client {client_address} disconnected. Total bytes received: {received_bytes}")

        except Exception as e:
            print(f"Error: {e}")

        finally:
            client_socket.close()
            print(f"Connection with {client_address} closed\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TCP Server with optional Nagle and Delayed ACK control")
    parser.add_argument('--disable-nagle', action='store_true', help="Disable Nagle's algorithm (TCP_NODELAY)")
    parser.add_argument('--disable-delayed-ack', action='store_true', help="Disable Delayed ACK (TCP_QUICKACK) if supported")
    parser.add_argument('--port', type=int, default=8080, help="Port to run the server on (default: 8080)")

    args = parser.parse_args()

    start_server(port=args.port, disable_nagle=args.disable_nagle, disable_delayed_ack=args.disable_delayed_ack)

