#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <json/json.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <thread>
#include <mutex>
#include <cstring>
#include <unistd.h>
#include <ctime>
#include <chrono>

class Peer {
public:
    Peer(std::string peer_host, int peer_port) : peer_host(peer_host), peer_port(peer_port) {
        id = std::make_pair(peer_host, peer_port);
        peer_socket = socket(AF_INET, SOCK_STREAM, 0);
        if (peer_socket == -1) {
            std::cerr << "Error creating socket" << std::endl;
            exit(EXIT_FAILURE);
        }

        peer_address.sin_family = AF_INET;
        peer_address.sin_addr.s_addr = INADDR_ANY;
        peer_address.sin_port = htons(peer_port);

        if (bind(peer_socket, (struct sockaddr *)&peer_address, sizeof(peer_address)) < 0) {
            std::cerr << "Binding failed" << std::endl;
            exit(EXIT_FAILURE);
        }

        listen(peer_socket, 5);
    }

    void outputWrite(std::string msg) {
        std::lock_guard<std::mutex> guard(lock_output);
        std::cout << msg << std::endl;
        std::ofstream outfile("output_" + std::to_string(peer_port) + ".txt", std::ios_base::app);
        outfile << msg << std::endl;
    }

    void outHandle(std::string timestamp, std::string id, std::string msg) {
        std::string out = "< " + timestamp + " > < " + id + " > < " + msg + " >";
        outputWrite(out);
    }

    void connectToSeed(std::string host, int port) {
        try {
            int seed_socket = socket(AF_INET, SOCK_STREAM, 0);
            if (seed_socket == -1) {
                std::cerr << "Error creating socket" << std::endl;
                return;
            }
            struct sockaddr_in seed_address;
            seed_address.sin_family = AF_INET;
            seed_address.sin_port = htons(port);
            inet_pton(AF_INET, host.c_str(), &seed_address.sin_addr);

            if (connect(seed_socket, (struct sockaddr *)&seed_address, sizeof(seed_address)) < 0) {
                std::cerr << "Connection failed" << std::endl;
                return;
            }

            std::string id_str = peer_host + ":" + std::to_string(peer_port);
            send(seed_socket, id_str.c_str(), id_str.size(), 0);

            char buffer[1024] = {0};
            recv(seed_socket, buffer, 1024, 0);
            std::vector<std::pair<std::string, int>> neigh_list;
            std::memcpy(neigh_list.data(), buffer, sizeof(neigh_list));
            for (auto& neigh : neigh_list) {
                peer_neighbour.insert(neigh);
            }

            close(seed_socket);
        } catch (...) {
            return;
        }
    }

    void connectToNeighbours() {
        for (auto& neighbour : peer_neighbour) {
            std::thread(&Peer::connectNeighbour, this, neighbour.first, neighbour.second).detach();
        }
    }

    void handleNeighbour(int neigh_socket, std::string id) {
        try {
            char buffer[1024] = {0};
            while (true) {
                recv(neigh_socket, buffer, 1024, 0);
                std::string peer_msg(buffer);
                // Handle the message
            }
        } catch (...) {
            return;
        }
    }

    void listenNeighbour() {
        try {
            while (true) {
                int neigh_socket;
                struct sockaddr_in neigh_address;
                socklen_t addrlen = sizeof(neigh_address);
                neigh_socket = accept(peer_socket, (struct sockaddr *)&neigh_address, &addrlen);
                if (neigh_socket < 0) {
                    std::cerr << "Accept failed" << std::endl;
                    continue;
                }
                char id_buffer[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &(neigh_address.sin_addr), id_buffer, INET_ADDRSTRLEN);
                std::string id(id_buffer);
                std::thread(&Peer::handleNeighbour, this, neigh_socket, id).detach();
                peer_neigh_socket_lst.push_back(neigh_socket);
                no_response_ct[neigh_socket] = 0;
            }
        } catch (...) {
            return;
        }
    }

    void start() {
        connectSeed();
        connectToNeighbours();
        std::thread(&Peer::listenNeighbour, this).detach();
    }

private:
    std::string peer_host;
    int peer_port;
    int peer_socket;
    struct sockaddr_in peer_address;
    std::pair<std::string, int> id;
    std::set<std::pair<std::string, int>> peer_neighbour;
    std::vector<int> peer_neigh_socket_lst;
    std::map<int, int> no_response_ct;
    std::mutex lock;
    std::mutex lock_output;
};

int main() {
    std::string host;
    int port;
    std::cout << "Please type the Host id of the peer = ";
    std::cin >> host;
    std::cout << "Please type the Port id of the peer = ";
    std::cin >> port;
    Peer peer(host, port);
    peer.start();
    while (true) {
        // Some main loop operations if needed
    }
    return 0;
}
