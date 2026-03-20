import os
import socket
import threading
import sys
import csv #hello

HOST = 'localhost' #change to '0.0.0.0' when testing on lab computers or localhost for laptop testing
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
processingCommands = []
UDPClients = {}
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registeredClient.csv')
processingCSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processingCommands.csv')
UDPClients = {}

with open(CSV_FILE, mode='r', newline='') as fille:
    reader = csv.reader(fille)
    for row in reader:
        RegisteredClients.append(tuple(row))

with open(CSV_FILE, mode='w', newline='') as theFile:
    writer = csv.writer(theFile)
    writer.writerow(['Client Name', 'IP Address', 'UDP Port'])

def writeToCSV():
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Client Name', 'IP Address', 'UDP Port'])
        for client in RegisteredClients:
            writer.writerow([client[0], client[1], client[2]])

def updateUserCommands():
    with open(processingCSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        for command in processingCommands:
            writer.writerow(command)
    


def checkUserRegistered(client_name, client_IP):
    for client in RegisteredClients:
        if client[0] == client_name and client[1] == str(client_IP):
            return True
    return False

def getDatafromClient(connection, client_address):
    try:
        while True:
            data = connection.recv(4096)
            if not data == "b''":
                print(f'received {data}', file=sys.stderr)
            if not data:
                break

            request = data.decode().strip()
            if not request:
                continue
            processingCommands.append(request)
            message = ""
            updateUserCommands()

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
                            if any((client[0] == client_name) or (client[1] == str(client_IP)) for client in RegisteredClients): #change and for multi client testing, back to or for single client per IP
                                message = f"REGISTER DENIED: RQ: {request_id} ALREADY REGISTERED"
                            else:
                                RegisteredClients.append((client_name, client_IP, client_UDP_Port))
                                #Justin Testing
                                clientSubjects.append([client_name])
                                print("clientSubjects", clientSubjects)
                                message = f"REGISTERED {request_id}"
                                writeToCSV()
            elif command == "Unregister":
                parts = request.split()
                if len(parts) < 3:
                    message = "UNREGISTER-DENIED: INVALID REQUEST FORMAT"
                else:
                    message = "UNREGISTERED " + parts[1]
                    client_name = str(parts[2]).lower()
                    if any((client[0] == client_name) or (client[1] == str(client_address[0])) for client in RegisteredClients):
                        
                        RegisteredClients.remove(client)

                        #Justin Testing
                        clientSubjects.remove([client_name])
                        print("clientSubjects", clientSubjects)

                        writeToCSV()
                        break
                    # for client in RegisteredClients:
                    #     if (client[0] == client_name) and (client[1] == str(client_address[0])):
                    #         RegisteredClients.remove(client)

                    #         #Justin Testing
                    #         clientSubjects.remove([client_name])
                    #         print("clientSubjects", clientSubjects)

                    #         writeToCSV()
                    #         break
                    else:
                        message = "NOT REGISTERED"
            elif command == "Update":
                parts = request.split()
                if len(parts) < 3:
                    message = "UPDATE-DENIED: INVALID REQUEST FORMAT"
                else:
                    request_id = parts[1]
                    client_name_raw = parts[2]
                    client_name = str(client_name_raw).lower()
                    
                    for client in RegisteredClients:
                        if (client[0] == client_name) or (client[1] == str(client_address[0])):
                            RegisteredClients.remove(client)
                            RegisteredClients.append((client_name, str(client_address[0]), str(parts[3])))

                            message = "UPDATE-CONFIRMED " + request_id + " " + client_name_raw + " " + client_address[0] + " " + parts[3]
                            writeToCSV()
                            break
                        else:
                            message = "UPDATE-DENIED " + request_id + " Name and IP not registered"
            elif command == "Subjects":
                counter = 0
                print(request)
                response = ''
                parts = request.split()
                client_name = str(parts[2]).lower()

                print(client_address)

                for item in parts[3:]:  # Skip command, request_id, and client_name; only process actual subjects
                    print(item) 
                    counter += 1
                    
                    #clientSubjects.append(item)

                    #Justin testing adding subjects to the clientSubjects list of lists
                    for name in clientSubjects:
                        if name[0] == client_name:
                            if item not in name:
                                name.append(item)

                    #clientSubjects[client_address[0]].append(item)
                    response += item + " "

                print(clientSubjects)
                message = "SUBJECTS UPDATED " + response

                
            elif command == "Quit":
                break
            else:
                message = "INVALID COMMAND"

            connection.sendall(message.encode())
            processingCommands.remove(request)
            updateUserCommands()

    finally:
        connection.close()


def getUDPDataFromClient():
    while True:
        data, addr = udpSock.recvfrom(4096)
        message = data.decode()
        parts = message.split()
        command = parts[0]

        message = ""
        # publish function
        if command == "Publish":
            rq = parts[1]
            name = parts[2]
            subject = parts[3]
            title = parts[4]
            text = " ".join(parts[5:])

            print(f"Publish received from {name}")

            if not any((client[0] == str(name).lower()) for client in RegisteredClients):
                message = f"PUBLISH-DENIED {rq} UserNotRegistered "
                udpSock.sendto(message.encode(), addr)
                continue

            UDPClients[name] = addr

            if not any(clientSubject == subject for clientSubject in clientSubjects):
                message = f"PUBLISH-DENIED {rq} SubjectNotRegistered"
                udpSock.sendto(message.encode(), addr)
                continue

            for user in clientSubjects:
                if subject in clientSubjects[user] and user != name:
                    if user in RegisteredClients:
                        user_addr = UDPClients[user]
                        messageToSend = f"MESSAGE {name} {subject} {title} {text}"
                        udpSock.sendto(messageToSend.encode(), user_addr)
                        print(f"Forwarding message to {user}")
            udpSock.sendto(
                f"PUBLISH-OK {rq}".encode(),
                addr
            )

        # publish comment function
        elif command == "PUBLISH-COMMENT":
            name = str(parts[1]).lower()
            subject = parts[2]
            title = parts[3]
            text = " ".join(parts[4:])

            print(f"Comment received from {name} on {subject}")

            for user in clientSubjects:
                if subject in clientSubjects[user]:
                    if user in RegisteredClients:
                        user_addr = UDPClients[user]
                        messageToSend = f"COMMENT {name} {subject} {title} {text}"
                        udpSock.sendto(messageToSend.encode(), user_addr)
                        print(f"Forwarding comment to {user}")

        elif command == "HELLO":

            name = parts[1]

            UDPClients[name] = addr

            print(f"UDP address registered for {name}: {addr}")

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_address = (HOST, PORT)
print(f'starting up on {HOST} port {PORT}', file=sys.stderr)
sock.bind(server_address)

# Server starts listening on the port
sock.listen(5)

udpConnectionThread = threading.Thread(target=getUDPDataFromClient)
udpConnectionThread.daemon = True
udpConnectionThread.start()

print('Server Running', file=sys.stderr, flush=True)
while True:
    # Wait for a connection
    connection, client_address = sock.accept()

    handleClientThread = threading.Thread(
        target=getDatafromClient,
        args=(connection, client_address,)
    )

    handleClientThread.daemon = True
    handleClientThread.start()