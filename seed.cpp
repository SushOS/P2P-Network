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

class SeedNode {
public:
    SeedNode(std::string host, int port) : host(host), port(port) {
        server_socket = socket(AF_INET, SOCK_STREAM, 0);
        if (server_socket == -1) {
            std::cerr << "Error creating socket" << std::endl;
            exit(EXIT_FAILURE);
        }

        server_address.sin_family = AF_INET;
        server_address.sin_addr.s_addr = INADDR_ANY;
        server_address.sin_port = htons(port);

        if (bind(server_socket, (struct sockaddr *)&server_address, sizeof(server_address)) < 0) {
            std::cerr << "Binding failed" << std::endl;
            exit(EXIT_FAILURE);
        }

        listen(server_socket, 5);
    }

    void outputWrite(std::string msg) {
        std::lock_guard<std::mutex> guard(lock_output);
        std::cout << msg << std::endl;
        std::ofstream outfile("seed_output" + std::to_string(port) + ".txt", std::ios_base::app);
        outfile << msg << std::endl;
    }

    void handleNode(int seed_socket, struct sockaddr_in peer_address) {
        char buffer[1024] = {0};
        inet_ntop(AF_INET, &(peer_address.sin_addr), buffer, INET_ADDRSTRLEN);
        std::string peer_ip(buffer);
        int peer_port = ntohs(peer_address.sin_port);

        std::string msg = std::to_string(port) + " seed node accepted connection from " + peer_ip + ":" + std::to_string(peer_port);
        outputWrite(msg);

        std::vector<std::pair<std::string, int>> neigh_list;
        for (auto& peer : peer_list) {
            neigh_list.push_back(peer);
        }

        send(seed_socket, &neigh_list[0], sizeof(neigh_list), 0);

        std::pair<std::string, int> peer_id;
        recv(seed_socket, &peer_id, sizeof(peer_id), 0);

        peer_list.push_back(peer_id);

        while (true) {
            char buffer[1024] = {0};
            int valread = recv(seed_socket, buffer, 1024, 0);
            if (valread == 0) {
                std::cerr << "Peer disconnected" << std::endl;
                break;
            }
            std::string msg_out = "I am seed with ip = [" + host + "," + std::to_string(port) + "] and this is the dead node id = " + buffer;
            outputWrite(msg_out);

            std::pair<std::string, int> dead_id;
            sscanf(buffer, "[%[^,],%d]", &(dead_id.first)[0], &dead_id.second);

            auto it = std::find(peer_list.begin(), peer_list.end(), dead_id);
            if (it != peer_list.end()) {
                peer_list.erase(it);
            }
        }
    }

    void connect() {
        while (true) {
            struct sockaddr_in client_address;
            int addrlen = sizeof(client_address);
            int client_socket = accept(server_socket, (struct sockaddr *)&client_address, (socklen_t*)&addrlen);
            if (client_socket < 0) {
                std::cerr << "Accept failed" << std::endl;
                continue;
            }
            std::thread t(&SeedNode::handleNode, this, client_socket, client_address);
            t.detach();
        }
    }

private:
    std::string host;
    int port;
    int server_socket;
    struct sockaddr_in server_address;
    std::vector<std::pair<std::string, int>> peer_list;
    std::mutex lock_output;
    std::mutex lock;
};

int main() {
    std::ifstream config_file("config.json");
    Json::Value config_data;
    config_file >> config_data;

    int N = config_data["N"].asInt();
    Json::Value seed_list = config_data["Seed_info"];
    std::cout << "The number of seed nodes = " << N << std::endl;

    std::vector<std::thread> threads;
    for (int i = 0; i < N; ++i) {
        std::string host = seed_list[i]["Host"].asString();
        int port = seed_list[i]["Port"].asInt();
        SeedNode seedNode(host, port);
        std::thread t(&SeedNode::connect, &seedNode);
        t.detach();
        threads.push_back(std::move(t));
    }

    for (auto& t : threads) {
        if (t.joinable()) {
            t.join();
        }
    }

    return 0;
}
