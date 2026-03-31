import os
import socket
import threading
import sys
import csv #hello

# Arrays and Global Variables


RegisteredClients = []
clientSubjects = []
availablePublications = []
clientThreads = []
processingCommands = []

numClients = 0
udpThread = None

# Server Selection

SERVER_SELECTION = 1
if SERVER_SELECTION == 1:
    HOST = 'localhost' #change to '0.0.0.0' when testing on lab computers or localhost for laptop testing
    CLIENTPORT = 10000
    SERVERPORT = 10003
    UDPHOST = '0.0.0.0' 
    UDPPORT = 8888

    otherHOST = 'localhost'
    otherServerClientPORT = 10001
    otherServerServerPORT = 10002
    otherUDPHOST = '0.0.0.0'
    otherUDPPORT = 8889
if SERVER_SELECTION == 2:
    HOST = 'localhost' 
    CLIENTPORT = 10001
    SERVERPORT = 10002
    UDPHOST = '0.0.0.0'
    UDPPORT = 8889

    otherHOST = 'localhost'
    otherServerClientPORT = 10000
    otherServerServerPORT = 10003
    otherUDPHOST = '0.0.0.0'
    otherUDPPORT = 8888

client_server_address = (HOST, CLIENTPORT)
server_server_address = (HOST, SERVERPORT)
otherClientServerAddress = (otherHOST, otherServerClientPORT)
otherServerServerAddress = (otherHOST, otherServerServerPORT)    

# Set up UDP socket for receiving publish/comment commands from clients

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

# CSV File Paths

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'registeredClient.csv')
processingCSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'processingCommands.csv')
userSubjects_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'userSubjects.csv')

# ================= General Helper Functions =================

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
            if command == "Quit":
                continue
            writer.writerow([command])

def readCSVInit():
    # Read from CSV to initialize RegisteredClients and clientSubjects, and clear CSV for new session
    oldCommands = []
    
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
            if row_name and row_ip and row_udp_port:
                RegisteredClients.append((row_name, row_ip, row_udp_port))

    with open(userSubjects_FILE, mode='r', newline='') as fill:
        reader = csv.reader(fill)
        for row in reader:
            normalized = normalize_subject_row(row)
            if normalized is not None and is_registered_client(normalized[0]):
                clientSubjects.append(normalized)

    with open(processingCSV_FILE, mode='r', newline='') as fille:
        reader = csv.reader(fille)
        for row in reader:
            oldCommands.append(tuple(row))

    writeToCSV()

    # Clear the CSV files for the new session
    with open(CSV_FILE, mode='w', newline='') as theFile:
       pass
    with open(userSubjects_FILE, mode='w', newline='') as theFil:
        pass
    with open(processingCSV_FILE, mode='w', newline='') as theFil:
        pass

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

    for command in processingCommands:
        parts = command.split()
        if len(parts) < 2:
            continue
        commandType = parts[0]
        if commandType == "Publish":
            UDPPublish(command, None)
        elif commandType == "Publish-Comment":
            UDPComment(command, None)

# ================= End General Helper Functions =================

# ================= TCP COMMANDS =================

def TCPRegister(request):
    parts = request.split()
    message = " "
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
                    numClients += 1 #Justin Testing, remove when done
                else:
                    #testing simple referring
                    if numClients < 1:
                        RegisteredClients.append((client_name, client_IP, client_UDP_Port))
                        #Justin Testing
                        clientSubjects.append([client_name])
                        print("clientSubjects", clientSubjects)
                        message = f"REGISTERED {request_id}"
                        writeToCSV()
                        numClients += 1
                    else:
                        message = "REFER " + request_id + " " + otherHOST + " " + str(otherServerClientPORT)
    return message

def TCPUnregister(request):
    parts = request.split()
    message = ""

    global numClients

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
    return message

def TCPUpdate(request):
    parts = request.split()
    message = ""

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
    return message

def TCPSubjects(request):
    response = ''
    message = ""
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

    return message

def TCPQuit(request):
    parts = request.split()
    client_name = str(parts[2]).lower()

    global numClients

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
        else:
            print("NOT REGISTERED SO CANNOT QUIT")

# ================= END TCP COMMANDS =================

# ================= UDP COMMANDS =================

def UDPPublish(request, addr):
    parts = request.split()

    if len(parts) < 6:
        udpSock.sendto("PUBLISH-DENIED INVALID-FORMAT".encode(), addr)
    rq = parts[1]
    name = parts[2]

    importantInfo = " ".join(parts[3:])
    importantParts = importantInfo.split("*")

    subject = importantParts[0][8:]          # Remove "Subj3ct:" prefix
    title = importantParts[1][7:]            # Remove "Titl3:" prefix
    text = " ".join(importantParts[2:])
    text = text[5:]                 # Remove "T3xt:" prefix

    sender_name = str(name).lower()

    if addr == None:
        if is_registered_client(sender_name):
            for client in RegisteredClients:
                if client[0] == sender_name:
                    addr = (client[1], int(client[2]))
                    break
        else:
            print(f"Cannot process command: sender {sender_name} not registered and no address provided.")
            return

    if not any((client[0] == sender_name) for client in RegisteredClients):
        message = f"PUBLISH-DENIED {rq} UserNotRegistered "
        udpSock.sendto(message.encode(), addr)

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

def UDPComment(request, addr):
    parts = request.split()

    rq = parts[1]
    name = str(parts[2]).lower()

    importantInfo = " ".join(parts[3:])
    importantParts = importantInfo.split("*S")

    subject = importantParts[0]
    title = importantParts[1][1:]  # Remove leading space from title
    text = " ".join(importantParts[2:])

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

# ================= END UDP COMMANDS =================

# ================= TCP and UDP Communication Functions =================
def getDatafromClient(connection, client_address):
    try:
        global numClients
        while True:
            data = connection.recv(4096)
            if not data == "b''":
                print(f'received {data}', file=sys.stderr)
            if not data:
                break

            request = data.decode().strip()
            if not request:
                continue

            message = ""
            command = request.split()[0]
            if command == "Register":
                message = TCPRegister(request)  
            elif command == "Unregister":
                message = TCPUnregister(request)
            elif command == "Update":
                message = TCPUpdate(request)
            elif command == "Subjects":
                message = TCPSubjects(request) 
            elif command == "Quit":
                TCPQuit(request)
                break
            else:
                message = "INVALID COMMAND"

            connection.sendall(message.encode())

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

        if command == "Publish":
            UDPPublish(request, addr)
        elif command == "Publish-Comment":
            UDPComment(request, addr)

        processingCommands.remove(request)
        updateUserCommands()

# ================= END TCP and UDP Communication Functions =================

# ================= Server-to-Server Communication Functions =================

def handleSendServertoServer (message):
    #open socket with other server, send the publish/comment command to other server
    print("Sending to other server:", message)
    sockToServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        global otherServerServerAddress
        sockToServer.connect(otherServerServerAddress)
        sockToServer.sendall(message.encode())

        received = ""
        data = sockToServer.recv(4096)
        if data:
            received += data.decode()
            print(f"Received from other server: {received}")
        else:
            print("No response received from other server.")

        sockToServer.close()
    except Exception as e:
        print(f"Error connecting to other server at {otherServerServerAddress}: {e}")

def handleReceiveServertoServer(connection):
    try:
        data = connection.recv(4096)
        if data:
            message = data.decode()
            print(f"Received from other server: {message}")
            connection.sendall(f"ACK: Received '{message}'".encode())
        else:
            print("No data received from other server.")
    except Exception as e:
        print(f"Error receiving data from other server: {e}")
    finally:
        connection.close()

# ================= End Server-to-Server Communication Functions =================


# Server Code
clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
otherServerServerAddress = (otherHOST, otherServerServerPORT)
print(f'starting up on {HOST} port {CLIENTPORT}', file=sys.stderr)

clientSock.bind(client_server_address)
serverSock.bind(server_server_address)

# Server starts listening on the port
clientSock.listen(5)
serverSock.listen(1)

udpConnectionThread = threading.Thread(target=getUDPDataFromClient)
udpConnectionThread.daemon = True
udpConnectionThread.start()

messageToServer = "Hello from server"
print('Server Running', file=sys.stderr, flush=True)

# Read from CSV to initialize RegisteredClients and clientSubjects, and clear CSV for new session
readCSVInit()

while True:
    # Wait for a connection
    
    # if SERVER_SELECTION == 1:
    #     serverToServerThread = threading.Thread(
    #             target=handleSendServertoServer,
    #             args=(messageToServer,)
    #         )
    #     serverToServerThread.daemon = True
    #     serverToServerThread.start()
    #     serverToServerThread.join()

    # if SERVER_SELECTION == 2:
    #     connection, client_address = serverSock.accept()
    #     serverToServerThread = threading.Thread(
    #             target=handleReceiveServertoServer,
    #             args=(connection,)
    #         )
    #     serverToServerThread.daemon = True
    #     serverToServerThread.start()
    #     serverToServerThread.join()

    clientConnection, client_address = clientSock.accept()
    handleClientThread = threading.Thread(
        target=getDatafromClient,
        args=(clientConnection, client_address,)
    )

    handleClientThread.daemon = True
    handleClientThread.start()