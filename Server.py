import os
import socket
import threading
import sys
import time
import csv #hello

HOST = 'localhost' #change to '0.0.0.0' when testing on lab computers
PORT = 10000

UDPHOST = "0.0.0.0"
UDPPORT = 8888

try:
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error as msg:
    print('Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    sys.exit()
try:
    udpSock.bind((UDPHOST, UDPPORT))
except socket.error as msg:
    print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    sys.exit()

clientThreads = []
udpThread = None
RegisteredClients = []
clientSubjects = []
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registeredClient.csv')

def writeToCSV():
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Client Name', 'IP Address', 'UDP Port'])
        for client in RegisteredClients:
            writer.writerow(client[0:3])
    print("Client information written to registeredClient.csv")



def getDatafromClient(connection, client_address):
    print('connection from %s' % (client_address,), file=sys.stderr)
    try:
        while True:
            data = connection.recv(4096)
            print(f'received {data}', file=sys.stderr)

            if not data:
                print('no more data from', client_address, file=sys.stderr)
                break

            request = data.decode().strip()
            if not request:
                continue

            command = request.split()[0]
            if command == "Register":
                parts = request.split()

                if len(parts) < 2:
                    message = "UNABLE TO REGISTER: INVALID REQUEST FORMAT"
                else:
                    request_id = parts[1]
                    if len(parts) < 3:
                        message = f"REGISTER DENIED: RQ: {request_id} CLIENT NAME NOT PROVIDED"
                    else:
                        if len(parts) < 5:
                            message = f"REGISTER DENIED: RQ: {request_id} IP ADDRESS NOT PROVIDED or PORT NOT PROVIDED"
                        else:
                            client_name = str(parts[2]).lower()
                            client_IP = str(parts[3])
                            client_UDP_Port = str(parts[4])
                            if any((client[0] == client_name) or (client[1] == client_IP) for client in RegisteredClients):
                                message = f"REGISTER DENIED: RQ: {request_id} ALREADY REGISTERED"
                            else:
                                RegisteredClients.append((client_name, client_IP, client_UDP_Port))
                                message = f"REGISTERED {request_id}"
                                writeToCSV()
                                    
                connection.sendall(message.encode())
            elif command == "Unregister":
                parts = request.split()
                if len(parts) < 3:
                    message = "UNREGISTER-DENIED: INVALID REQUEST FORMAT"
                else:
                    message = "UNREGISTERED " + parts[1]
                    client_name = str(parts[2]).lower()
                    for client in RegisteredClients:
                        if client[0] == client_name or client[1] == str(client_address[0]):
                            RegisteredClients.remove(client)
                            writeToCSV()
                            break
                    else:
                        message = "NOT REGISTERED"
                connection.sendall(message.encode())
            elif command == "Update":
                parts = request.split()
                if len(parts) < 3:
                    message = "UPDATE-DENIED: INVALID REQUEST FORMAT"
                else:
                    request_id = parts[1]
                    client_name_raw = parts[2]
                    client_name = str(client_name_raw).lower()
                    message = "UPDATE-CONFIRMED " + request_id + " " + client_name_raw + " " + client_address[0]
                    for client in RegisteredClients:
                        if client[0] == client_name and client[1] == client_address[0]:
                            RegisteredClients.remove(client)
                            RegisteredClients.append((client_name, client_address[0], client[2]))
                            writeToCSV()
                            break
                    else:
                        message = "UPDATE-DENIED " + request_id + " Name and IP not registered"
                connection.sendall(message.encode())

            elif command == "Subjects":
                counter = 0
                print(request)
                response = ''
                for item in request.split():
                    print(item)
                    counter += 1
                    if counter > 3:
                        clientSubjects.append(item)
                        response += item + " "

                print(clientSubjects)

                message = "SUBJECTS UPDATED " + response
                
                connection.sendall(message.encode())
            elif command == "Quit":
                break
            else:
                message = "INVALID COMMAND"
                connection.sendall(message.encode())
    finally:
        print('closing connection to', client_address, file=sys.stderr, flush=True)
        connection.close()
    
def getUDPDataFromClient():
    try:
        while True:
            data = udpSock.recvfrom(4096)
            message = data[0].decode()
            addr = data[1]
            print(f"Received {message} from {addr}")
            
            udpSock.sendto(message.encode(), addr)
    finally:
        time.sleep(0.2)
        udpSock.close()

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOST, PORT)
print(f'starting up on {HOST} port {PORT}', file=sys.stderr)
sock.bind(server_address)

# Server starts listening on the port
sock.listen(5)

# Start the UDP listener once, as a daemon so it doesn't block shutdown
udpThread = threading.Thread(target=getUDPDataFromClient, daemon=True)
udpThread.start()

while True:
    # Wait for a connection
    print('waiting for a connection', file=sys.stderr, flush=True)

    connection, client_address = sock.accept()
    handleClientThread = threading.Thread(target=getDatafromClient, args=(connection, client_address,))
    handleClientThread.start()
    clientThreads.append(handleClientThread)