import socket
import threading
import json
import random
import time
import hashlib
import math
import datetime
import os

MESSAGE_SIZE = 1024
MAX_PEERS = 4
MAX_MSG_PER_PEER = 10
MSG_INTERVAL = 5
LIVENESS_CHECK_INTERVAL = 13
OUTPUT_FILE = "output.txt"
seed_nodes = []
current_dir = os.path.dirname(os.path.abspath(__file__))


class PeerNode:
    def __init__(self, p_host, p_port, config_data):
        """
        Constructor to initialize the Peer Node
        1. Initialize the Peer Node with the host and port
        2. Create a socket for the Peer Node
        3. Listen for incoming connections from the peers
        4. Initialize the list of chosen peers and the list of chosen seeds
        5. Initialize the message list and the message count
        6. Initialize the dead map which help to keep track of the dead nodes or no. of request failed in liveness check
        7. Initialize the list of seed connections
        """

        self.p_host = p_host
        self.p_port = p_port
        self.id = f"{p_host}:{p_port}"
        self.p_address = (self.p_host, self.p_port)
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_socket.bind(self.p_address)
        self.peer_socket.listen()
        self.neigh_socket_lst = []
        self.chosen_peers = set()
        self.chosen_seeds = []
        self.config_data = config_data
        self.msg_lst = {}
        self.msg_cnt = 0
        self.lock = threading.Lock()
        self.lock_output = threading.Lock()
        self.dead_map = {}
        self.seed_conn = []
        self.socket_id = {}

    def outout_write(self, msg):
        """
        Write the output to the file for each Peer Node
        And Lock ensures that the common resource is not corrupted
        """

        self.lock_output.acquire()
        out_filename = f"output{self.p_host}{self.p_port}.txt"
        out_path = os.path.join(current_dir, out_filename)
        with open(out_path, "a") as file:
            file.write(msg + "\n")
        self.lock_output.release()

    def SeedCount_To_Choose(self):
        """
        Returns the number of seed nodes to choose from the list of seed nodes
        """

        n = len(seed_nodes)
        return math.floor(n / 2) + 1

    def connect_to_seeds(self):
        """
        Connect to the Seed Nodes
        1. Choose the seed nodes from the list of seed nodes
        2. Connect to the chosen seed nodes
        3. Send the REGISTER message to the seed nodes
        """

        self.chosen_seeds = random.sample(seed_nodes, self.SeedCount_To_Choose())
        for s_host, s_port in self.chosen_seeds:
            try:
                seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                seed_socket.connect((s_host, s_port))
                seed_socket.sendall(f"REGISTER {self.p_host} {self.p_port}".encode())
                msg = f"The peer connected to seed node at {s_host}:{s_port}"
                print(msg)
                self.outout_write(msg)
            except Exception as e:
                msg = f"Failed to connect to the seed node at {s_host}:{s_port}, {e}"
                print(msg)

    def get_peer_lists(self):
        """
        Get the peer lists from the chosen seed nodes
        1. Send the GET PEER LIST message to the seed nodes
        2. Get the peer lists from the seed nodes
        """

        connected_peers = set()
        for s_host, s_port in self.chosen_seeds:
            try:
                seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                seed_socket.connect((s_host, s_port))
                seed_socket.sendall("GET PEER LIST".encode())
                peer_list = seed_socket.recv(MESSAGE_SIZE).decode().split(",")
                self.seed_conn.append(seed_socket)
                msg = f"The peer list sent by the seed is : {peer_list}"
                print(msg)
                self.outout_write(msg)
                connected_peers = connected_peers.union(set(peer_list))
                msg = (
                    f"Connected peers to seed {s_host}:{s_port} are : {connected_peers}"
                )
                print(msg)
                self.outout_write(msg)
            except Exception as e:
                msg = f"Failed to get the peer nodes from the seed at {s_host}:{s_port}, {e}"
                print(msg)
        return connected_peers

    def connect_to_peers(self):
        """
        Connect to the Peers in the Network
        1. Choose the peers from the peer list
        2. Connect to the chosen peers
        3. Start the Gossip_Network and Liveliness_Check threads for the connected peers
        """

        connected_peers = self.get_peer_lists()
        connected_peers = list(connected_peers)
        chosen_peers = random.sample(
            connected_peers, min(len(connected_peers), MAX_PEERS)
        )
        chosen_peers.remove(f"{self.p_host}:{self.p_port}")
        msg = f"The chosen peers are : {chosen_peers}"
        print(msg)
        self.outout_write(msg)
        for peer_details in chosen_peers:
            peer_details = peer_details.split(":")
            msg = f"The peer details are : {peer_details}"
            print(msg)
            self.outout_write(msg)
            peer_host, peer_port = peer_details[0], int(peer_details[1])
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_host, peer_port))
                self.socket_id[peer_socket] = (peer_host, peer_port)
                self.chosen_peers.add((peer_host, peer_port))
                self.neigh_socket_lst.append(peer_socket)
                msg = f"Connected to peer at {peer_host}:{peer_port}"
                print(msg)
                self.outout_write(msg)
                threading.Thread(
                    target=self.Gossip_Network, args=(peer_socket,)
                ).start()
                threading.Thread(
                    target=self.Liveliness_Check, args=(peer_socket,)
                ).start()
                threading.Thread(
                    target=self.handle_peer_connection, args=(peer_socket,)
                ).start()
            except Exception as e:
                msg = f"Error connecting to peer {peer_host}:{peer_port}, {e}"
                print(msg)
        else:
            pass

    def handle_listen_peers(self, nbr_sock):
        """
        Handles the incoming connections from the peers
        1. Receives the Gossip of Liveness Request from the peer
        2. If it is Gossip, then Broadcast the message to the other peers
        """

        try:
            while True:
                req = nbr_sock.recv(MESSAGE_SIZE)
                req = req.decode()
                print(req)
                if req.startswith("Gossip"):
                    threading.Thread(target=self.Forward_Message, args=(req,)).start()
        except:
            msg = "Error in handle_listen_peers"
            print(msg)

    def listen_peers(self):
        """
        Handles listening to the incoming connections from the peers
        And Starts a new thread to handle the request from the peer
        """

        try:
            while True:
                nbr_sock, id = self.peer_socket.accept()
                threading.Thread(
                    target=self.handle_listen_peers, args=(nbr_sock,)
                ).start()
        except Exception as e:
            msg = f"Error in listen_peers : {e}"
            print(msg)

    def Send_Message(self, socket, msg):
        """
        Simply sends the message to the all the peers connected with the current peer
        """

        socket.sendall(msg.encode())

    def Forward_Message(self, msg):
        """
        Help to broadcast the message to the peers
        1. Generate the hash of the message
        2. If the message is already broadcasted, then return
        3. If the message is not broadcasted, then add the message to the message list
        4. Broadcast the message to the peers
        """

        message_hash = hashlib.sha256(msg.encode()).hexdigest()
        if message_hash in self.msg_lst:
            return
        if message_hash not in self.msg_lst:
            self.msg_lst[message_hash] = set()
        for socket in self.neigh_socket_lst:
            try:
                self.msg_lst[message_hash].add(socket)
                msg = f"Message broadcasted to {socket.getpeername()}"
                print(msg)
                self.outout_write(msg)
                threading.Thread(target=self.Send_Message, args=(socket, msg))
            except Exception as e:
                msg = "Exception in broadcast"
                print(msg)

    def generateGossipMessage(self, host, port):
        """
        Generate the Gossip Message of the form "Gossip:TimeStamp:Host:Port"
        """

        message = ""
        message += "Gossip:"
        # Get the current timestamp
        message += datetime.datetime.now().time().strftime("%Y-%m-%d %H:%M:%S")
        message += ":"
        message += host
        message += ":"
        message += str(port)
        return message

    def Gossip_Network(self, socket):
        """
        Gossip the messages to the peers in the network
        """

        try:
            count = MAX_MSG_PER_PEER
            while count > 0:
                msg = self.generateGossipMessage(
                    socket.getpeername()[0], socket.getpeername()[1]
                )
                socket.sendall(msg.encode())
                count = count - 1
                time.sleep(MSG_INTERVAL)
        except:
            print("Error in Gossip_Network")

    def generateLivenessMessage(self, host, port):
        """
        Generate the Liveliness Message of the form "Liveliness:TimeStamp:Host:Port"
        """

        message = ""
        message += "Liveliness:"
        message += datetime.datetime.now().time().strftime("%Y-%m-%d %H:%M:%S")
        message += ":"
        message += host
        message += ":"
        message += str(port)
        return message

    def Liveliness_Check(self, sock):
        """
        Check the liveliness of the Peers in the Network by Sending Liveliness Messages
        And If 3 Consecutive Liveliness Checks Fail, then Notify the Seed Nodes
        """

        try:
            while True:
                try:
                    msg = self.generateLivenessMessage(
                        sock.getpeername()[0], sock.getpeername()[1]
                    )
                    sock.sendall(msg.encode())
                    self.dead_map[sock] = 0
                except:
                    if sock not in self.dead_map:
                        self.dead_map[sock] = 1
                    else:
                        self.dead_map[sock] += 1

                    if self.dead_map[sock] == 3:
                        for s_host, s_port in self.chosen_seeds:
                            try:
                                seed_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_STREAM
                                )
                                seed_socket.connect((s_host, s_port))
                                deadnode = self.socket_id[sock]
                                msg = (
                                    "DEAD NODE " + deadnode[0] + " " + str(deadnode[1])
                                )
                                seed_socket.sendall(msg.encode())
                            except Exception as e:
                                print(
                                    "Failed to send details of dead node to seed node"
                                )
                time.sleep(LIVENESS_CHECK_INTERVAL)
        except:
            print("Error in Liveliness_Check")

    
    def handle_peer_connection(self, peer_socket):
        try:
            while True:
                req = peer_socket.recv(MESSAGE_SIZE)
                req = req.decode()
                print(req)
                if req.startswith("Gossip"):
                    threading.Thread(target=self.Forward_Message, args=(req,)).start()
        except Exception as e:
            print(f"Error handling peer connection: {e}")


if __name__ == "__main__":
    # Read the configuration file to get Seed Node Details
    with open("./config_file.json") as config_file:
        config_data = json.load(config_file)
    # Extract the number of seed nodes and their addresses
    seed_addresses = config_data["Seed_addresses"]
    for seed_info in seed_addresses:
        host = seed_info.get("Host")
        port = seed_info.get("Port")
        seed_nodes.append((host, port))

    # Get the Peer Node details from the user
    host = input("Enter the host address of the peer node: ")
    port = int(input("Enter the port number of the peer node: "))

    # Create a Peer Node and connect to the Seed Nodes
    peer = PeerNode(host, port, config_data)
    peer.connect_to_seeds()
    peer.get_peer_lists()
    peer.connect_to_peers()

    # Start the Peer Node to listen to the incoming connections from the peers in Separate Thread
    threading.Thread(target=peer.listen_peers).start()
