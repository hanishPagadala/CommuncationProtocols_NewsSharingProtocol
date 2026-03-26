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
availablePublications = []
UDPClients = {}
numClients = 0

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registeredClient.csv')
processingCSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processingCommands.csv')
userSubjects_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'userSubjects.csv')


def normalize_subject_row(row):
    if not row:
        return None

    name = str(row[0]).strip().lower()
    if not name or name == 'client subjects':
        return None

    subjects = []
    for item in row[1:]:
        cleaned = str(item).strip()
        if cleaned:
            subjects.append(cleaned)

    return [name, *subjects]


def is_registered_client(name):
    return any(client[0] == name for client in RegisteredClients)
        

def writeToCSV():
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Client Name', 'IP Address', 'UDP Port'])
        for client in RegisteredClients:
            writer.writerow([client[0], client[1], client[2]])

    with open(userSubjects_FILE, mode='w', newline='') as fil:
        writer = csv.writer(fil)
        for subjects in clientSubjects:
            normalized = normalize_subject_row(subjects)
            if normalized is not None and is_registered_client(normalized[0]):
                writer.writerow(normalized)

def updateUserCommands():
    with open(processingCSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        for command in processingCommands:
            writer.writerow([command])


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
                                message = f"REGISTER DENIED: {request_id} ALREADY REGISTERED"
                                global numClients
                                numClients += 1
                            else:
                                
                                if numClients < 1:
                                    RegisteredClients.append((client_name, client_IP, client_UDP_Port))
                                    #Justin Testing
                                    clientSubjects.append([client_name])
                                    print("clientSubjects", clientSubjects)
                                    message = f"REGISTERED {request_id}"
                                    writeToCSV()
                                    numClients += 1
                                else:
                                    message = "REFER " + request_id + " " 
                    
            elif command == "Unregister":
                client_name = str(parts[2]).lower()
                for client in RegisteredClients:
                    print(client[0], client_name)
                    if (client[0] == client_name):
                        RegisteredClients.remove(client)

                        #Justin Testing
                        message = "UNREGISTERED " + parts[1]
                        numClients -= 1

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
                print(request)
                response = ''
                parts = request.split()
                listOfSubjects = " ".join(parts[3:])
                splitSubjects = [item.strip() for item in listOfSubjects.split(",") if item.strip()]
                client_name = str(parts[2]).lower()

                for name in clientSubjects:
                    if name[0] == client_name:
                        clientSubjects.remove(name)
                        
                clientSubjects.append([client_name])
                for name in clientSubjects:
                    if name[0] == client_name:
                        for item in splitSubjects:  # Skip command, request_id, and client_name; only process actual subjects
                            name.append(item)
                            response += item + " "
                
                writeToCSV()
                print(clientSubjects)
                message = "SUBJECTS UPDATED " + response

                
            elif command == "Quit":
                parts = request.split()
                client_name = str(parts[2]).lower()
                for client in RegisteredClients:
                    if (client[0] == client_name):
                        RegisteredClients.remove(client)

                        #Justin Testing
                        numClients -= 1

                        for subject in clientSubjects:
                            if subject[0] == client_name:
                                clientSubjects.remove(subject)

                        print("clientSubjects", clientSubjects)

                        writeToCSV()

                        print("QUIT CONFIRMED")
                        break
                    else:
                        print("NOT REGISTERED SO CANNOT QUIT")
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
        request = data.decode()
        parts = request.split()
        if not parts:
            continue
        command = parts[0]


        processingCommands.append(request)
        updateUserCommands()
        print("Processing Commands:", processingCommands)

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
            title = parts[4][6:]
            text = " ".join(parts[6:])
            sender_name = str(name).lower()

            print(f"Publish received from {name}")

            if not any((client[0] == sender_name) for client in RegisteredClients):
                message = f"PUBLISH-DENIED {rq} UserNotRegistered "
                udpSock.sendto(message.encode(), addr)
                continue

            UDPClients[name] = addr

            for client in RegisteredClients:
                if len(client) < 3:
                    continue

                client_name = str(client[0]).lower()
                client_ip = client[1]
                client_port = client[2]
                
                for userSubjects in clientSubjects:
                    if subject in userSubjects[1:]:
                        try:
                            user_addr = (client_ip, int(client_port))
                        except ValueError:
                            print(f"Skipping invalid UDP port for client entry: {client}")
                            continue
                        
                        messageToSend = f"Message {name} {subject} {title} {text}"

                        if not any( (publication[0] == subject) and (publication[1] == title) for publication in availablePublications):
                            availablePublications.append((subject, title))
                        if len(availablePublications) < 1:
                            availablePublications.append((subject, title))

                        udpSock.sendto(messageToSend.encode(), user_addr) 
                        continue                     
                    else:
                        print(f"Skipping {client_name} for publish: not subscribed to {subject}")
                        continue

            udpSock.sendto(
                f"PUBLISH-OK {rq}".encode(),
                addr
            )

        # publish comment function
        elif command == "Publish-Comment":
            name = str(parts[2]).lower()
            subject = parts[3]
            title = parts[4]
            text = " ".join(parts[5:])

            print(f"Comment received from {name} on {subject}")

            for client in RegisteredClients:
                if len(client) < 3:
                    continue

                client_name = str(client[0]).lower()
                client_ip = client[1]
                client_port = client[2]
                
                for publications in availablePublications:
                    if (publications[0] == subject) and (publications[1] == title):

                        for userSubjects in clientSubjects:
                            if subject in userSubjects[1:]:
                                try:
                                    user_addr = (client_ip, int(client_port))
                                except ValueError:
                                    print(f"Skipping invalid UDP port for client entry: {client}")
                                    continue
                                
                                messageToSend = f"Comment {name} {subject} {title} {text}"

                                udpSock.sendto(messageToSend.encode(), user_addr)                      
                            else:
                                print(f"Skipping {client_name} for comment: not subscribed to {subject}")
                                continue


            udpSock.sendto(
                f"COMMENT-OK {rq}".encode(),
                addr
            )

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

with open(userSubjects_FILE, mode='r', newline='') as fill:
    reader = csv.reader(fill)
    for row in reader:
        normalized = normalize_subject_row(row)
        if normalized is not None and is_registered_client(normalized[0]):
            clientSubjects.append(normalized)

with open(CSV_FILE, mode='w', newline='') as theFile:
    writer = csv.writer(theFile)
    writer.writerow(['Client Name', 'IP Address', 'UDP Port'])

writeToCSV()

for subject in clientSubjects:
    print(subject[0])

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
    # if parts[len(parts) - 1] == "TCP":
    #     processingCommands.remove(command)
    #     getDatafromClient(commandToRun.encode(), ("", ""))

print(processingCommands)
for command in processingCommands:
    parts = command.split()
    if len(parts) < 2:
        continue
    

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