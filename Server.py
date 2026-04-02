import os
import socket
import threading
import sys
import csv #hello

# Arrays and Global Variables

clientThreads = []
RegisteredClients = []
clientPasswords = []
clientSubjects = []
processingCommands = []
availablePublications = []

numClients = 0
udpThread = None

referedLast = False

# Server Selection

SERVER_SELECTION = 2
if SERVER_SELECTION == 1:
    HOST = 'localhost' #change to '0.0.0.0' when testing on lab computers or localhost for laptop testing
    CLIENTPORT = 10000
    SERVERPORT = 10003
    UDPHOST = '0.0.0.0' 
    UDPPORT = 8888
    client_server_address = (HOST, CLIENTPORT)
    server_server_address = (HOST, SERVERPORT)
    otherHOST = 'localhost'
    otherClientPORT = 10001
    otherServerPORT = 10002
    otherClientServerAddress = (otherHOST, otherClientPORT)
    otherServerServerAddress = (otherHOST, otherServerPORT)
    otherUDPHOST = '0.0.0.0'
    otherUDPPORT = 8889
    RegisteredClientsCSV = 'registeredClient.csv'
    clientPasswordCSV = 'clientPasswords.csv'
if SERVER_SELECTION == 2:
    HOST = 'localhost' 
    CLIENTPORT = 10001
    SERVERPORT = 10002
    client_server_address = (HOST, CLIENTPORT)
    server_server_address = (HOST, SERVERPORT)
    UDPHOST = '0.0.0.0'
    UDPPORT = 8889
    otherHOST = 'localhost'
    otherClientPORT = 10000
    otherServerPORT = 10003
    otherClientServerAddress = (otherHOST, otherClientPORT)
    otherServerServerAddress = (otherHOST, otherServerPORT)
    otherUDPHOST = '0.0.0.0'
    otherUDPPORT = 8888
    RegisteredClientsCSV = 'registeredClient2.csv'
    clientPasswordCSV = 'clientPasswords2.csv'

# Set up UDP socket for receiving publish/comment commands from clients

try:
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error as msg:
    print('Failed to create socket. Error: ' + str(msg))
    sys.exit()
try:
    udpSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udpSock.bind((UDPHOST, UDPPORT))
except socket.error as msg:
    print('Bind failed. Error: ' + str(msg))
    sys.exit()

# CSV File Paths

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), RegisteredClientsCSV)
clientPassword_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), clientPasswordCSV)
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

def extract_marked_field(value, prefix):
    cleaned = str(value).strip()
    if cleaned.startswith(prefix):
        return cleaned[len(prefix):].strip()
    return cleaned

def writeToCSV():
    with open(CSV_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Client Name', 'IP Address', 'UDP Port', "Password"])
        for client in RegisteredClients:
            writer.writerow([client[0], client[1], client[2], "client[4]"])

    with open(userSubjects_FILE, mode='w', newline='') as fil:
        writer = csv.writer(fil)
        for subjects in clientSubjects:
            normalized = normalize_subject_row(subjects)
            if normalized is not None and is_registered_client(normalized[0]):
                writer.writerow(normalized)

def writeToPasswordCSV():
    with open(clientPassword_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Client Name', 'Password'])
        for client in clientPasswords:
            writer.writerow([client[0], client[1]])

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

    with open(clientPasswordCSV, mode='r', newline='') as fille:
        reader = csv.reader(fille)
        for row in reader:
            if len(row) < 2:
                continue
            clientPasswords.append((row[0].strip().lower(), row[1].strip()))

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
        # if parts[len(parts) - 1] == "TCP":
        #     processingCommands.remove(command)
        #     getDatafromClient(commandToRun.encode(), ("", ""))

# ================= End General Helper Functions =================

# ================= TCP COMMANDS =================

def TCPRegister(request):
    parts = request.split()
    message = " "
    global referedLast

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
                client_Pass = parts[5] if len(parts) > 5 else ""

                if any((client[0] == client_name) for client in RegisteredClients): #change and for multi client testing, back to or for single client per IP
                    message = f"REGISTER DENIED: {request_id} ALREADY REGISTERED"
                    global numClients
                    numClients += 1 #Justin Testing, remove when done
                else:
                    #testing simple referring
                    if numClients < 1 and referedLast == False:
                        registeredOnOther = True
                        registeredOnOther = handleSendServertoServer(request, waitForAck=True) 

                        print(clientPasswords)

                        if registeredOnOther:
                            message = f"REGISTER DENIED: {request_id} REGISTERED ON OTHER SERVER"
                        elif registeredOnOther == False:
                            if any(((clientPass[0] == client_name) and (clientPass[1] != client_Pass)) for clientPass in clientPasswords):
                                message = f"REGISTER DENIED: {request_id} INCORRECT PASSWORD"
                            else:
                                RegisteredClients.append((client_name, client_IP, client_UDP_Port, client_Pass))
                                #Justin Testing
                                clientSubjects.append([client_name])
                                message = f"REGISTERED {request_id}"
                                writeToCSV()

                                if not any(((clientPass[0] == client_name)) for clientPass in clientPasswords):
                                    clientPasswords.append((client_name, client_Pass))
                                    writeToPasswordCSV()

                                numClients += 1
                                referedLast = True
                    else:
                        message = "REFER " + request_id + " " + otherHOST + " " + str(otherClientPORT)
                        referedLast = False
    return message

def TCPUnregister(request):
    parts = request.split()
    if len(parts) < 3:
        return "UNREGISTER-DENIED: INVALID REQUEST FORMAT"

    message = "NOT REGISTERED"

    global numClients

    client_name = str(parts[2]).lower()
    for client in RegisteredClients:
        if (client[0] == client_name):
            RegisteredClients.remove(client)

            #Justin Testing
            message = "UNREGISTERED " + parts[1]
            numClients -= 1

            for subject in clientSubjects:
                if subject[0] == client_name:
                    clientSubjects.remove(subject)

            writeToCSV()
            break
    return message

def TCPUpdate(request, client_ip):
    parts = request.split()
    message = ""

    if len(parts) < 4:
        message = "UPDATE-DENIED: INVALID REQUEST FORMAT"
    else:
        request_id = parts[1]
        client_name_raw = parts[2]
        client_name = str(client_name_raw).lower()
        new_udp_port = str(parts[3])

        try:
            int(new_udp_port)
        except ValueError:
            return "UPDATE-DENIED " + request_id + " INVALID UDP PORT"
        
        for client in RegisteredClients:
            if (client[0] == client_name):
                
                clientIP = client[1]
                clientName = client[0]
                clientPassword = client[4] if len(client) > 4 else ""

                RegisteredClients.remove(client)
                RegisteredClients.append((clientName, str(clientIP), new_udp_port, clientPassword)) # Name, IP, UDP Socket

                message = "UPDATE-CONFIRMED " + request_id + " " + client_name_raw + " " + str(client_ip) + " " + new_udp_port
                writeToCSV()
                break
            else:
                message = "UPDATE-DENIED " + request_id + " Name and IP not registered"
    return message

def TCPSubjects(request):
    response = ''
    message = ""
    parts = request.split()
    if len(parts) < 4:
        return "SUBJECTS-DENIED INVALID REQUEST FORMAT"

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
    message = "SUBJECTS UPDATED " + response

    return message

def TCPQuit(request):
    parts = request.split()
    if len(parts) < 3:
        return

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
            writeToCSV()

            print("QUIT CONFIRMED")
            break

# ================= END TCP COMMANDS =================

# ================= UDP COMMANDS =================

def UDPPublish(request, addr):
    parts = request.split()

    if len(parts) < 6:
        if addr is not None:
            udpSock.sendto("PUBLISH-DENIED INVALID-FORMAT".encode(), addr)
        return
    rq = parts[1]
    name = parts[2]

    importantInfo = " ".join(parts[3:])
    importantParts = importantInfo.split("*")

    subject = extract_marked_field(importantParts[0], "Subj3ct:")
    title = extract_marked_field(importantParts[1], "Titl3:")
    text = extract_marked_field(" ".join(importantParts[2:]), "T3xt:")

    sender_name = str(name).lower()

    # If sender is not registered, deny the publish/comment and return
    if (addr is not None) and (is_registered_client(sender_name) == False):
        udpSock.sendto(f"PUBLISH-DENIED {rq} UserNotRegistered".encode(), addr)
        return 

    # if not any((client[0] == sender_name) for client in RegisteredClients):
    #     message = f"PUBLISH-DENIED {rq} UserNotRegistered "
    #     if addr is not None:
    #         udpSock.sendto(message.encode(), addr)
    #     return

    if not any( (publication[0] == subject) and (publication[1] == title) for publication in availablePublications):
        availablePublications.append((subject, title))
    if len(availablePublications) < 1:
        availablePublications.append((subject, title))
    
    for client in RegisteredClients:
        if len(client) < 3:
            continue

        client_name = str(client[0]).lower()
        client_ip = client[1]
        client_port = client[2]
        
        for userSubjects in clientSubjects:
            if userSubjects[0] == client_name and subject in userSubjects[1:]:
                try:
                    user_addr = (client_ip, int(client_port))
                except ValueError:
                    continue
                
                messageToSend = f"Message {name} {subject} {title} {text}"

                udpSock.sendto(messageToSend.encode(), user_addr) 
                continue                     
            else:
                continue

    if addr is not None:
        udpSock.sendto(
            f"PUBLISH-OK {rq}".encode(),
            addr
        )

def UDPComment(request, addr):
    parts = request.split()

    if len(parts) < 6:
        if addr is not None:
            udpSock.sendto("COMMENT-DENIED INVALID-FORMAT".encode(), addr)
        return

    rq = parts[1]
    name = str(parts[2]).lower()

    importantInfo = " ".join(parts[3:])
    importantParts = importantInfo.split("*")

    subject = extract_marked_field(importantParts[0], "Subj3ct:")
    title = extract_marked_field(importantParts[1], "Titl3:")
    text = extract_marked_field(" ".join(importantParts[2:]), "Comm3nt:")

    # If sender is not registered, deny the publish/comment and return
    if (addr is not None) and (is_registered_client(name.lower()) == False):
        udpSock.sendto(f"COMMENT-DENIED {rq} UserNotRegistered".encode(), addr)
    return 

    # if not any((client[0] == name) for client in RegisteredClients):
    #     if addr is not None:
    #         udpSock.sendto(f"COMMENT-DENIED {rq} UserNotRegistered".encode(), addr)
    #     return

    for client in RegisteredClients:
        if len(client) < 3:
            continue

        client_name = str(client[0]).lower()
        client_ip = client[1]
        client_port = client[2]
        
        for publications in availablePublications:
            if (publications[0] == subject) and (publications[1] == title):  
                for userSubjects in clientSubjects:
                    if userSubjects[0] == client_name and subject in userSubjects[1:]:
                        try:
                            user_addr = (client_ip, int(client_port))
                        except ValueError:
                            continue
                        
                        messageToSend = f"Comment {name} {subject} {title} {text}"
                        print("Sending comment to: " + client_name)
                        udpSock.sendto(messageToSend.encode(), user_addr)                      
                    else:
                        continue

    if addr is not None:
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
            if not data:
                break
            print("TCP: " + data.decode())

            request = data.decode().strip()
            if not request:
                continue
              
            message = ""
            command = request.split()[0]
            userRegistered = False

           # Make sure user is registered before allowing any commands other than register

            if command == "Register":
                message = TCPRegister(request)  
            else:
                if is_registered_client(request.split()[2].lower()):
                    if command == "Unregister":
                        message = TCPUnregister(request)
                    elif command == "Update":
                        message = TCPUpdate(request, client_address[0])
                    elif command == "Subjects":
                        message = TCPSubjects(request) 
                    elif command == "Quit":
                        TCPQuit(request)
                        break
                    else:
                        message = "INVALID COMMAND"
                else:
                    message = f"{command} - DENIED {request.split()[1]} User Not Registered."

            connection.sendall(message.encode())

    finally:
        connection.close()

def getUDPDataFromClient():
    while True:
        data, addr = udpSock.recvfrom(4096)
        request = data.decode()
        print(f"UDP: {request}")

        handleSendServertoServer(request, waitForAck=False) #send original request to other server        

        parts = request.split()
        if not parts:
            continue
        command = parts[0]

        processingCommands.append(request)
        updateUserCommands()

        if is_registered_client(parts[2].lower()):
            if command == "Publish":
                UDPPublish(request, addr)
            elif command == "Publish-Comment":
                UDPComment(request, addr)
        else:
            udpSock.sendto(f"{command} - DENIED {parts[1]} User Not Registered".encode(), addr)

        processingCommands.remove(request)
        updateUserCommands()

# ================= END TCP and UDP Communication Functions =================

# ================= Server-to-Server Communication Functions =================

def handleSendServertoServer (message, waitForAck : bool):
    #open socket with other server, send the publish/comment command to other server
    sockToServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        global otherServerServerAddress
        sockToServer.connect(otherServerServerAddress)
        sockToServer.sendall(message.encode())
        
        if waitForAck == True:
            received = ""
            data = sockToServer.recv(4096)
            if data:
                received += data.decode()
                print(f"Received from other server (IM IN handleSendServertoServer): {received}")
                if received == "REGISTER-ACCEPT":
                    return False
                elif received == "REGISTER-DENY":
                    return True

    except Exception as e:
        print(f"Error connecting to other server at {otherServerServerAddress}: {e}")
    finally:
        sockToServer.close()


def handleReceiveServertoServer(connection):
    try:
        data = connection.recv(4096)
        if data:
            message = data.decode()
            print(f"Server-to-Server (IM IN handleReceiveServertoServer): {message}")

            parts = message.split()
            if not parts:
                return

            request = parts[0] #Justin testing for receiving specific message types
            client = parts[2] if len(parts) > 2 else ""
            outbound = ""

            if request == "Register":
                if is_registered_client(client):
                    outbound = "REGISTER-DENY"
                else:
                    outbound = "REGISTER-ACCEPT"
                connection.sendall(outbound.encode())
            elif request == "Publish":
                UDPPublish(message, None)
            elif request == "Publish-Comment":
                UDPComment(message, None)
    except Exception as e:
        print(f"Error receiving data from other server: {e}")
    finally:
        connection.close()

def listenServertoServer():
    global serverSock
    while True:
        connection, server2_address = serverSock.accept()
        handleReceiveServertoServer(connection)

# ================= End Server-to-Server Communication Functions =================


# Server Code
clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
otherServerServerAddress = (otherHOST, otherServerPORT)

clientSock.bind(client_server_address)
serverSock.bind(server_server_address)

# Server starts listening on the port
clientSock.listen(5)
serverSock.listen(1)

udpConnectionThread = threading.Thread(target=getUDPDataFromClient)
udpConnectionThread.daemon = True
udpConnectionThread.start()

messageToServer = "Hello from server"

# Read from CSV to initialize RegisteredClients and clientSubjects, and clear CSV for new session
readCSVInit()

serverToServerThread = threading.Thread(
    target=listenServertoServer,
    args=()
)
serverToServerThread.daemon = True
serverToServerThread.start()

while True:
    #Wait for a connection
    
    clientConnection, client_address = clientSock.accept()
    handleClientThread = threading.Thread(
        target=getDatafromClient,
        args=(clientConnection, client_address,)
    )

    handleClientThread.daemon = True
    handleClientThread.start()