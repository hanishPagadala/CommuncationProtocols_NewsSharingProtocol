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
        

with open(processingCSV_FILE, mode='w', newline='') as theFile:
    writer = csv.writer(theFile)
    #writer.writerow(["command"])

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
            if command == "Quit TCP" or command == "Quit UDP":
                continue
            writer.writerow([command])


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
            processingCommands.append(str(request) + " TCP")
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
                            if any((client[0] == client_name) for client in RegisteredClients): #change and for multi client testing, back to or for single client per IP
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
                    client_name = str(parts[2]).lower()
                    for client in RegisteredClients:
                        print(client[0], client_name)
                        if (client[0] == client_name):
                            RegisteredClients.remove(client)

                            #Justin Testing
                            message = "UNREGISTERED " + parts[1]
                            
                            for subject in clientSubjects:
                                if subject[0] == client_name:
                                    clientSubjects.remove(subject)

                            print("clientSubjects", clientSubjects)

                            writeToCSV()
                            break
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
                        if (client[0] == client_name):
                            RegisteredClients.remove(client)
                            RegisteredClients.append((client_name, str(client_address[0]), str(parts[3]))) # Name, IP, UDP Socket

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
                listOfSubjects = " ".join(parts[3:])
                splitSubjects = listOfSubjects.split(",") 
                print(listOfSubjects)
                client_name = str(parts[2]).lower()

                print(client_address)

                # for item in parts[3:]:  # Skip command, request_id, and client_name; only process actual subjects
                #     print(item) 
                #     counter += 1
                    
                #     #clientSubjects.append(item)

                #     #Justin testing adding subjects to the clientSubjects list of lists
                    
                    

                #     #clientSubjects[client_address[0]].append(item)
                #     response += item + " "

                for name in clientSubjects:
                    if name[0] == client_name:
                        clientSubjects.remove(name)
                        
                clientSubjects.append([client_name])
                for name in clientSubjects:
                    if name[0] == client_name:
                        for item in splitSubjects:  # Skip command, request_id, and client_name; only process actual subjects
                            name.append(item)
                            response += item + " "
                print("The Client Subjects are" + str(clientSubjects))
                message = "SUBJECTS UPDATED " + response

                
            elif command == "Quit":
                break
            else:
                message = "INVALID COMMAND"

            connection.sendall(message.encode())
            #processingCommands.remove(request)
            #updateUserCommands()

    finally:
        connection.close()


def getUDPDataFromClient():
    while True:
        data, addr = udpSock.recvfrom(4096)
        message = data.decode()
        parts = message.split()
        if not parts:
            continue
        command = parts[0]

        message = ""
        # publish function
        # change it to command.lower()
        if command == "Publish":
            if len(parts) < 6:
                udpSock.sendto("PUBLISH-DENIED INVALID-FORMAT".encode(), addr)
                continue

            rq = parts[1]
            name = parts[2]
            subject = parts[3]
            title = parts[4]
            text = " ".join(parts[5:])
            sender_name = str(name).lower()

            print(f"Publish received from {name}")

            if not any((client[0] == sender_name) for client in RegisteredClients):
                message = f"PUBLISH-DENIED {rq} UserNotRegistered "
                udpSock.sendto(message.encode(), addr)
                continue

            UDPClients[name] = addr

            # if not any(clientSubject == subject for clientSubject in clientSubjects):
            #     message = f"PUBLISH-DENIED {rq} SubjectNotRegistered"
            #     udpSock.sendto(message.encode(), addr)
            #     continue

            for client in RegisteredClients:
                if len(client) < 3:
                    continue

                client_name = str(client[0]).lower()
                client_ip = client[1]
                client_port = client[2]

                # Do not send publish messages back to the publisher.
                if client_name == sender_name:
                    continue

                try:
                    user_addr = (client_ip, int(client_port))
                except ValueError:
                    print(f"Skipping invalid UDP port for client entry: {client}")
                    continue

                messageToSend = f"PUBLISH {name} {subject} {title} {text}"
                print(f"Forwarding publish to {client_name}")
                udpSock.sendto(messageToSend.encode(), user_addr)
                                

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

with open(CSV_FILE, mode='r', newline='') as fille:
    reader = csv.reader(fille)
    for row in reader:
        if len(row) < 3:
            continue

        row_name = row[0].strip().lower()
        row_ip = row[1].strip()
        row_udp_port = row[2].strip()

        # Ignore CSV header lines and malformed rows.
        if row_name == 'client name':
            continue

        try:
            int(row_udp_port)
        except ValueError:
            continue

        RegisteredClients.append((row_name, row_ip, row_udp_port))

with open(CSV_FILE, mode='w', newline='') as theFile:
    writer = csv.writer(theFile)
    writer.writerow(['Client Name', 'IP Address', 'UDP Port'])

oldCommands = []

with open(processingCSV_FILE, mode='r', newline='') as fille:
    reader = csv.reader(fille)
    for row in reader:
        oldCommands.append(tuple(row))

for command in oldCommands:
    request = ""
    for subCommand in command:
        request += str(subCommand) + " "
    processingCommands.append(request)

for command in processingCommands:
    parts = command.split()
    if len(parts) < 2:
        continue
    counter = 0
    commandToRun = ""
    for item in parts:
        if counter >= len(parts) - 1:
            break
        commandToRun += parts[counter] + " "
        counter += 1
    if parts[len(parts) - 1] == "TCP":
        processingCommands.remove(command)
        getDatafromClient(commandToRun.encode(), ("", ""))

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