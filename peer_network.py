import socket
import threading
import json
import random

MESSAGE_SIZE = 1024
MAX_PEERS = 4

class peerNode:
    def __init__(self, p_host, p_port, config_data):
        self.p_host = p_host
        self.p_port = p_port
        self.p_address = (self.p_host, self.p_port)
        self.chosen_peers = set()
        self.chosen_seeds = []
        self.config_data = config_data        

    def start(self):
        threading.Thread(target=self.broadcast_msg).start()
        threading.Thread(target=self.check_peer_liveness).start()
    
    def get_b_half_n(self):
        n = len(seed_nodes)
        return n // 2
    
    def connect_to_seeds(self):
        self.chosen_seeds = random.sample(seed_nodes, self.get_b_half_n() + 1)
        for s_host, s_port in self.chosen_seeds:
            try:
                seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                seed_socket.connect((s_host, s_port))
                seed_socket.sendall(f"REGISTER {self.p_host} {self.p_port}".encode())
                seed_socket.close()
                print(f"The peer connected to seed node at {s_host}:{s_port}")
            except Exception as e:
                print(f"Failed to connect to the seed node at {s_host}:{s_port}, {e}")
    
    def get_peer_lists(self):
        connected_peers = []
        for (s_host, s_port) in self.chosen_seeds:
            try:
                seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                seed_socket.connect((s_host, s_port))
                seed_socket.sendall("GET PEER LIST")
                peer_list = seed_socket.recv(MESSAGE_SIZE).decode().split(",")
                connected_peers.extend(peer_list)
                seed_socket.close()

            except Exception as e:
                print(f"Failed to get the peer nodes from the seed at {s_host}:{s_port}, {e}")
        return connected_peers
    
    def connect_to_peers(self):
        all_connected_peers = self.get_peer_lists()
        chosen_peers = random.sample(all_connected_peers, min(len(all_connected_peers), MAX_PEERS))
        for peer_details in chosen_peers:
            peer_host, peer_port = peer_details[0], peer_details[1]
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_host, peer_port))
                self.chosen_peers.add((peer_host, peer_port))
                peer_socket.close()
                print(f"Connected to peer at {peer_host}:{peer_port}")
            except Exception as e:
                print(f"Error connecting to peer {peer_host}:{peer_port}, {e}")
        
    # def check_peer_liveness(self):
    #     fail_cnt = 0
    #     while fail_cnt<3:


    # def broadcast_msg(self):

def main():
    with open('./config_file.json') as config_file:
        config_data = json.load(config_file)
    global seed_nodes
    seed_nodes = []
    seed_addresses = config_data["Seed_addresses"]
    for seed_info in seed_addresses:
        host = seed_info.get("Host")
        port = seed_info.get("Port")
        seed_nodes.append((host, port))

    peer = peerNode("127.0.0.1", 54321, config_data)
    peer.connect_to_seeds()
    peer.connect_to_peers()
    peer.start()

if __name__ == "__main__":
    main()