import socket
import threading
import json
import random
import time
import hashlib
import datetime

MESSAGE_SIZE = 1024
MAX_PEERS = 4
MAX_MSG_PER_PEER = 10
MSG_INTERVAL = 5
LIVENESS_CHECK = 13
OUTPUT_FILE = "output.txt"
seed_nodes = []


class peerNode:
    def __init__(self, p_host, p_port, config_data):
        self.p_host = p_host
        self.p_port = p_port
        self.p_address = (self.p_host, self.p_port)
        self.peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peer_socket.bind((self.p_host, self.p_port))
        self.peer_socket.listen()
        self.neigh_socket_lst = []
        self.chosen_peers = set()
        self.chosen_seeds = []
        self.config_data = config_data
        self.msg_lst = (
            {}
        )  # A dictionary of message hashes. As hashes are one to one functions, each hash corresponds to a single value
        self.msg_cnt = 0
        self.timestamp = 0.0
        self.dead_map = {}
        self.seed_conn = []

    # ------------------------------------------------------------------------------------------
    # def start(self):
    #     threading.Thread(target=self.broadcast_msg).start()
    #     threading.Thread(target=self.liveness).start()
    # ------------------------------------------------------------------------------------------
    def choose_nodes(self):
        n = len(seed_nodes)
        return (n // 2) + 1

    # ------------------------------------------------------------------------------------------
    def connect_to_seeds(self):
        self.chosen_seeds = random.sample(seed_nodes, self.choose_nodes())
        for s_host, s_port in self.chosen_seeds:
            try:
                seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                seed_socket.connect((s_host, s_port))
                seed_socket.sendall(f"REGISTER {self.p_host} {self.p_port}".encode())
                # seed_socket.close()
                print(f"The peer connected to seed node at {s_host}:{s_port}")
            except Exception as e:
                print(f"Failed to connect to the seed node at {s_host}:{s_port}, {e}")

    # ------------------------------------------------------------------------------------------
    def get_peer_lists(self):
        connected_peers = set()
        for s_host, s_port in self.chosen_seeds:
            try:
                seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                seed_socket.connect((s_host, s_port))
                seed_socket.sendall("GET PEER LIST".encode())
                peer_list = seed_socket.recv(MESSAGE_SIZE).decode().split(",")
                self.seed_conn.append(seed_socket)
                print(f"The peer list sent by the seed is : {peer_list}")
                connected_peers = connected_peers.union(set(peer_list))
                # seed_socket.close()
                print(
                    f"Connected peers to seed {s_host}:{s_port} are : {connected_peers}"
                )
            except Exception as e:
                print(
                    f"Failed to get the peer nodes from the seed at {s_host}:{s_port}, {e}"
                )
        return connected_peers

    # #------------------------------------------------------------------------------------------
    def connect_to_peers(self):
        connected_peers = self.get_peer_lists()
        connected_peers = list(connected_peers)
        chosen_peers = random.sample(
            connected_peers, min(len(connected_peers), MAX_PEERS)
        )
        chosen_peers.remove(f"{self.p_host}:{self.p_port}")
        print(f"The chosen peers are : {chosen_peers}")
        for peer_details in chosen_peers:
            peer_details = peer_details.split(":")
            print(f"The peer details are : {peer_details}")
            peer_host, peer_port = peer_details[0], int(peer_details[1])
            try:
                peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                peer_socket.connect((peer_host, peer_port))
                self.chosen_peers.add((peer_host, peer_port))
                self.neigh_socket_lst.append(peer_socket)
                print(f"Connected to peer at {peer_host}:{peer_port}")
                threading.Thread(target=self.gossip_in_net, args=(peer_socket,)).start()
                threading.Thread(
                    target=self.liveliness_in_net, args=(peer_socket,)
                ).start()
            except Exception as e:
                print(f"Error connecting to peer {peer_host}:{peer_port}, {e}")
        else:
            pass

    def handle_listem_peers(self, nbr_sock):
        try:
            while True:
                req = nbr_sock.recv(MESSAGE_SIZE)
                req = req.decode()
                print(req)
                if "liveliness" not in req:
                    threading.Thread(target=self.broadcast_msg, args=(req,)).start()

        except:
            print("Error in handle_listen_peers")

    def listen_peers(self):
        try:
            while True:
                nbr_sock, id = self.peer_socket.accept()
                threading.Thread(
                    target=self.handle_listem_peers, args=(nbr_sock,)
                ).start()

                # if not req:
                #     continue
                # if req[0] == "GOSSIP":
                #     threading.Thread(target=self.broadcast_msg, args=(self, req[1]))
                # elif req[0] == "LIVENESS_CHECK":
                #     req = json.dumps(["LIVENESS_REPLY", datetime.now().time().strftime("%Y-%m-%d %H:%M:%S") , req[2], self.id])
                #     nbr_sock.sendall(req.encode())
        except Exception as e:
            print(e)

    # #------------------------------------------------------------------------------------------
    def gossip_msg(self):
        self.timestamp = float(time.time())
        return f"{self.timestamp}:{self.p_host}:{self.msg_cnt+1}"

    # #------------------------------------------------------------------------------------------

    def broadcast(self, socket, msg):
        socket.sendall(msg.encode())

    def broadcast_msg(self, msg):
        message_hash = hashlib.sha256(msg.encode()).hexdigest()
        if message_hash in self.msg_lst:
            return
        if message_hash not in self.msg_lst:
            self.msg_lst[message_hash] = (
                set()
            )  # we have created a set as a particular node can send the message to the connected node at most once
        for socket in self.neigh_socket_lst:
            try:
                self.msg_lst[message_hash].add(socket)
                print(f"Message broadcasted ")
                threading.Thread(target=self.broadcast, args=(socket, msg))

            except Exception as e:
                print("Exception in broadcast")

    def gossip_in_net(self, socket):
        try:
            count = MAX_MSG_PER_PEER
            while count > 0:
                num = random.randint(1, 100000)
                socket.sendall(f"This is gossip Message {num}".encode())
                count = count - 1
                time.sleep(MSG_INTERVAL)
        except:
            print("Error in gossip_in_net")

    def handle_dead_peer(self, socket):
        num = random.randint(1, 1000000)
        msg = "This is dead node"
        socket.sendall(msg.encode())

    def liveliness_in_net(self, sock):
        try:
            while True:
                try:
                    num = random.randint(1, 100000)
                    sock.sendall(f"This is a liveliness Message {num}".encode())
                except:
                    if sock not in self.dead_map:
                        self.dead_map[sock] = 1
                    else:
                        self.dead_map[sock] += 1

                    if self.dead_map[sock] == 3:
                        print("check")
                        for s_host, s_port in self.chosen_seeds:
                            try:
                                seed_socket = socket.socket(
                                    socket.AF_INET, socket.SOCK_STREAM
                                )
                                seed_socket.connect((s_host, s_port))
                                seed_socket.sendall("Dead found".encode())

                            except Exception as e:
                                print(
                                    f"Failed to get the peer nodes from the seed at {s_host}:{s_port}, {e}"
                                )
                time.sleep(MAX_MSG_PER_PEER)

        except:
            print("Error in liveliness")

    # #------------------------------------------------------------------------------------------
    def liveness(self):
        consec_fails = 0
        while consec_fails < 3:
            for frnd_host, frnd_port in self.chosen_peers:
                try:
                    frnd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    frnd_socket.connect((frnd_host, frnd_port))
                    req = json.dumps(
                        [
                            "LIVENESS_CHECK",
                            datetime.now().time().strftime("%Y-%m-%d %H:%M:%S"),
                            self.id,
                        ]
                    )
                    frnd_socket.sendall(req.encode())
                    resp = frnd_socket.recv(MESSAGE_SIZE).decode()
                    if resp[0] == "LIVENESS_REPLY":
                        consec_fails = 0  # reset the number of fails
                        print(f"Peer {frnd_host}:{frnd_port}")
                except Exception as e:
                    consec_fails += 1
                    if consec_fails >= 3:
                        self.notify_seed(frnd_host, frnd_port)
                        self.chosen_peers.remove((frnd_host, frnd_port))
                        print(f"Peer {frnd_host}:{frnd_port} is DEAD...")
            time.sleep(
                LIVENESS_CHECK
            )  # Wait for 13 seconds to check the liveness of the next Node.


if __name__ == "__main__":
    with open("./config.json") as config_file:
        config_data = json.load(config_file)
    seed_addresses = config_data["Seed_addresses"]
    for seed_info in seed_addresses:
        host = seed_info.get("Host")
        port = seed_info.get("Port")
        seed_nodes.append((host, port))

    host = input("Enter the host address of the peer node: ")
    port = int(input("Enter the port number of the peer node: "))
    peer = peerNode(host, port, config_data)
    peer.connect_to_seeds()
    peer.get_peer_lists()
    peer.connect_to_peers()
    threading.Thread(target=peer.listen_peers).start()