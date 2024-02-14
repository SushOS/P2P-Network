import socket
import threading
import json
import os

MESSAGE_SIZE = 1024
current_dir = os.path.dirname(os.path.abspath(__file__))


class SeedNode:
    # Constructor to initialize the Seed Node
    def __init__(self, host, port):
        self.connected_peers = set()
        self.s_host = host
        self.s_port = port
        self.id = f"{host}:{port}"
        self.seed_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.seed_socket.bind((self.s_host, self.s_port))
        self.lock_output = threading.Lock()
        self.lock = threading.Lock()
        self.seed_socket.listen()

    def outout_write(self, msg):
        """
        Write the output to the file for each Seed Node
        And Lock ensures that the common resource is not corrupted
        """

        self.lock_output.acquire()
        out_filename = f"seed{self.s_host}{self.s_port}.txt"
        out_path = os.path.join(current_dir, out_filename)
        with open(out_path, "a") as file:
            file.write(msg + "\n")
        self.lock_output.release()

    # Method to start the Seed Node
    def Start_Seed(self):
        """
        Method to start the Seed Node
        1. Listen for incoming connections from peers
        2. Handle the request of different peers in separate threads
        """

        print(f"The seed node is listening at {self.s_host}:{self.s_port}")
        while True:
            peer_socket, peer_address = self.seed_socket.accept()
            msg = f"A peer from {peer_address} has connected."
            print(msg)
            self.outout_write(msg)
            threading.Thread(
                target=self.Handle_Peer_Request, args=(peer_socket,)
            ).start()

    def Handle_Peer_Request(self, peer_socket):
        """
        Method to handle the different type of peer requests
        1. REGISTER : Add the peer to the connected peers list
        2. GET PEER LIST : Send the peer list to the peer
        3. DEAD NODE : Remove the dead node from the connected peers list
        """

        while True:
            try:
                request = peer_socket.recv(MESSAGE_SIZE).decode()
                if request.startswith("REGISTER"):
                    self.Add_To_PeerList(request.split()[1], int(request.split()[2]))
                elif request == "GET PEER LIST":
                    self.Send_PeerList(peer_socket)
                elif request.startswith("DEAD NODE"):
                    self.Remove_DeadNode(request.split()[2], int(request.split()[3]))
                    msg = (
                        "DEAD NODE FOUND : "
                        + request.split()[2]
                        + ":"
                        + request.split()[3]
                    )
                    print(msg)
                    self.outout_write(msg)
            except:
                pass

    def Send_PeerList(self, peer_socket):
        """
        Method to send the peer list to the peer
        """

        peerlist = ",".join(
            [f"{peer[0]}:{peer[1]}" for peer in list(self.connected_peers)]
        )
        peer_socket.sendall(peerlist.encode())
        msg = f"Sent peer list to {peer_socket.getpeername()[0]}:{peer_socket.getpeername()[1]}"
        print(msg)
        self.outout_write(msg)

    def Add_To_PeerList(self, host, port):
        """
        Method to add the peer to the connected peers list
        """

        self.connected_peers.add((host, port))
        msg = f"New peer at {host}:{port} is now registered."
        print(msg)
        self.outout_write(msg)

    def Remove_DeadNode(self, host, port):
        """
        Method to remove the dead node from the connected peers list
        """

        if (host, port) in self.connected_peers:
            self.connected_peers.remove((host, port))
            msg = f"The node at {host}:{port} was dead and is now removed."
            print(msg)
            self.outout_write(msg)


if __name__ == "__main__":
    # Read the configuration file to get Seed Node Details
    with open("./config.json") as config_file:
        config_data = json.load(config_file)

    # Extract the number of seed nodes and their addresses
    N = config_data["num_seeds"]

    print(f"The number of Seed nodes in the network is : {N}")

    seed_addresses = config_data["Seed_addresses"]
    for seed_info in seed_addresses:
        host = seed_info.get("Host")
        port = seed_info.get("Port")
        seed_node = SeedNode(host, port)

        # Start the Processing of Seed Node in a separate thread
        seed_thread = threading.Thread(target=seed_node.Start_Seed).start()
