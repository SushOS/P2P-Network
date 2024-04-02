<center> <h1>P2P(Peer to Peer) Network</h1> </center>

# Team Members

<h3> 1. Sushant Ravva (B21CS084)
<h3> 2. Jaysukh Makvana (B21CS043)

# Overview

- P2P is the network which helps us to communicate between two nodes without the need of centralized server.
- It means every node of P2P Network acts as a Server(Send Response) as well as Client(Open Request).
- Our Network consists of 2 types of nodes:
  1. <b>Seed Node</b>: Initial points of contact for the all peer nodes
  2. <b>Peer Node</b>: Actively participate in the network by sharing information
- We have added functionalities to avoid sending same message multiple time over certain links and also avoids sending message to the peer node which is not activiely part of the network(Dead Node).

# Input Format

- We will use the seed node those are pre-defined in the `config.json` file. You can re-configure it as per your need.
- Define `num_seeds` as total number of seeds you wanted to start.
- Then define `Seed_addresses` as the JSON Object containing key-value pair for the `Host` and `Port`.

# How to Run ?

- In your PC just Copy-Paste all 3 files `peer.py`, `seed.py` and `config.json` and change the seed number and address of the seed nodes in config file.
- Now run below command in different terminal window:

1. To Run the Seed File

```
python seed.py
```

2. To Run the Peer File

```
python peer.py
```

- After running the Peer file enter the Host Address and Port for the Peer Node in the terminal.
- Now, you can see the Connected List of Nodes for the Given Peer in the Terminal.
- And your connection will be established properly.

# Workflow of Code

- On running seed node it started listening on the seed address defined in the `config.json` file.
- After that when we register new peer node on the network it will choose `floor(n/2) + 1` seed node randomly and get peer connected with them. And finally choose at max 4 random peers from obtained peer list and make connection with them.
- Now, Every peer will start sending gossip message as well as liveliness message. And also replying to the liveliness message.
- And If 3 consecutive liveness check message passed for any peer node then it's neighbour sent that data to the all the connected seed and tell seed node to remove the data of that file.
- To obtain this all parallel processing we have used python inbuilt library `threading`.

# Output Format

- You can see output for each node in their respective terminal.
