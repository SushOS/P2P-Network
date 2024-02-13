import socket
import threading
import json

MESSAGE_SIZE = 1024

class seedNode:
    def __init__(self, host, port):
        self.connected_peers = set()
        self.s_host = host
        self.s_port = port
        self.s_address = (self.s_host, self.s_port)
    #------------------------------------------------------------------------------------------
    def startseed(self):
        self.seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.seed_socket.bind((self.s_host, self.s_port))
        self.seed_socket.listen()
        print(f"The seed node is listening at {self.s_host}:{self.s_port}")

        while True:
            peer_socket, peer_address = self.seed_socket.accept()
            print(f"A peer from {peer_address} has connected.")
            threading.Thread(target= self.handle_peer, args=(peer_socket,)).start()
    #------------------------------------------------------------------------------------------
    def handle_peer(self, peer_socket):
        request = peer_socket.recv(MESSAGE_SIZE).decode()

        if request.startswith("REGISTER"):
            self.add_peer(request.split()[1], int(request.split()[2]))
        elif request == "GET PEER LIST":
            self.send_peerlist(peer_socket)
        elif request.startswith("DEAD_NODE"):
            self.remove_dead_node(request.split()[1], int(request.split()[2]))
        elif request == "LIVENESS CHECK":
            peer_socket.sendall("ALIVE".encode())
        peer_socket.close()
    #------------------------------------------------------------------------------------------
    def send_peerlist(self, peer_socket):
        peerlist = ",".join([f"{peer[0]}:{peer[1]}" for peer in self.connected_peers])
        peer_socket.sendall(peerlist.encode())
        print(f"Sent peer list to {peer_socket.getpeername()[0]}:{peer_socket.getpeername()[1]}")
    #------------------------------------------------------------------------------------------
    def add_peer(self, host, port):
        self.connected_peers.add((host, port))
        print(f"New peer at {host}:{port} is now registered.")
    #------------------------------------------------------------------------------------------
    def remove_dead_node(self, host, port):
        if (host, port) in self.connected_peers:
            self.connected_peers.remove((host, port))
            print(f"The node at {host}:{port} was dead and is now removed.")
    #------------------------------------------------------------------------------------------
            
def main():
    with open('./config_file.json') as config_file:
        config_data = json.load(config_file)

    N = config_data["num_seeds"]
    print(f"The number of Seed nodes in the network is : {N}")
    seed_addresses = config_data["Seed_addresses"]
    for seed_info in seed_addresses:
        host = seed_info.get("Host")
        port = seed_info.get("Port")
        seed_node = seedNode(host, port)
        seed_thread = threading.Thread(target=seed_node.startseed)
        seed_thread.start()

if __name__ == "__main__":
    main()