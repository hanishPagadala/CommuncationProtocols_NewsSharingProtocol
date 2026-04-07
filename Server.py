import os
import socket
import threading
import csv
import time
import builtins
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox

# Arrays and Global Variables

clientThreads = []
RegisteredClients = []
clientPasswords = []
clientSubjects = []
processingCommands = []
availablePublications = []

udpSock = None
udpThread = None
udpStopEvent = threading.Event()
clientSock = None
udpConnectionThread = None
serverToServerThread = None
serverMainThread = None
serverStopEvent = threading.Event()

root = None
log_widget = None
status_label = None
state_widget = None

serverRunning = False

real_print = print


def gui_print(*args):
    message = " ".join(map(str, args))
    if root is not None and log_widget is not None:
        root.after(0, lambda: log_widget.insert(tk.END, message + "\n"))
        root.after(0, lambda: log_widget.see(tk.END))
    real_print(message)

ackLock = threading.Lock()
ackCondition = threading.Condition(ackLock)
pendingRegisterAcks = {}

referedLast = False

# Synchronize shared in-memory state and CSV persistence across threads.
stateLock = threading.RLock()

# Server Selection (default is 1, changed by user at startup configuration dialog)
SERVER_SELECTION = 1
HOST = socket.gethostbyname(socket.gethostname())
otherHOST = 'localhost' #default value, changed by user at startup configuration dialog
TCPPort = 10000
UDPPort = 20000

# CSV file paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE_DIR, 'registeredClient.csv')
clientPassword_FILE = os.path.join(BASE_DIR, 'clientPasswords.csv')
processingCSV_FILE = os.path.join(BASE_DIR, 'processingCommands.csv')
userSubjects_FILE = os.path.join(BASE_DIR, 'userSubjects.csv')

def apply_server_configuration(selection, other_server_host):
    global SERVER_SELECTION, HOST, TCPPort, UDPPort, otherHOST

    if selection not in (0, 1):
        raise ValueError("Server selection must be 0 or 1")

    SERVER_SELECTION = selection
    otherHOST = str(other_server_host).strip() or 'localhost'

def prompt_startup_configuration():
    while True:
        selection = simpledialog.askinteger(
            "Server Setup",
            "Select server instance (0 or 1):",
            parent=root,
            minvalue=0,
            maxvalue=1,
            initialvalue=SERVER_SELECTION
        )
        if selection is None:
            return False

        peer_host = simpledialog.askstring(
            "Server Setup",
            "Enter the other server IP/host:",
            parent=root,
            initialvalue=otherHOST
        )
        if peer_host is None:
            return False

        peer_host = peer_host.strip()
        if not peer_host:
            messagebox.showerror("Invalid Input", "Other server IP/host cannot be empty.")
            continue

        apply_server_configuration(selection, peer_host)
        return True

# Networking sockets are created when the UI starts the server.

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
    with stateLock:
        return any(client[0] == name for client in RegisteredClients)        

def extract_marked_field(value, prefix):
    cleaned = str(value).strip()
    if cleaned.startswith(prefix):
        return cleaned[len(prefix):].strip()
    return cleaned

def writeToCSV():
    with stateLock:
        with open(CSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Client Name', 'IP Address', 'UDP Port', "Password"])
            for client in RegisteredClients:
                writer.writerow([client[0], client[1], client[2], client[4] if len(client) > 4 else ""])

        with open(userSubjects_FILE, mode='w', newline='') as fil:
            writer = csv.writer(fil)
            for subjects in clientSubjects:
                normalized = normalize_subject_row(subjects)
                if normalized is not None and is_registered_client(normalized[0]):
                    writer.writerow(normalized)

def writeToPasswordCSV():
    with stateLock:
        with open(clientPassword_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Client Name', 'Password'])
            for client in clientPasswords:
                writer.writerow([client[0], client[1]])

def updateUserCommands():
    with stateLock:
        with open(processingCSV_FILE, mode='w', newline='') as file:
            writer = csv.writer(file)
            for command in processingCommands:
                if command == "Quit":
                    continue
                writer.writerow([command])

def readCSVInit():
    # Read from CSV to initialize RegisteredClients and clientSubjects, and clear CSV for new session
    oldCommands = []
    
    with stateLock:
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
                if (len(row) < 2) or (row[0].strip().lower() == 'client name'):
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
    global referedLast, SERVER_SELECTION

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

                with stateLock:
                    alreadyRegistered = any((client[0] == client_name) for client in RegisteredClients)

                if alreadyRegistered: #change and for multi client testing, back to or for single client per IP
                    message = f"REGISTER DENIED: {request_id} ALREADY REGISTERED"
                else:
                    #testing simple referring
                    registeredOnOther = True
                    registeredOnOther = handleSendServertoServer(request, waitForAck=True) 

                    if int(client_IP[-1])%2 == SERVER_SELECTION:
                        if registeredOnOther:
                            message = f"REGISTER DENIED: {request_id} REGISTERED ON OTHER SERVER"
                        elif registeredOnOther == False:
                            with stateLock:
                                if any(((clientPass[0] == client_name) and (clientPass[1] != client_Pass)) for clientPass in clientPasswords):
                                    message = f"REGISTER DENIED: {request_id} INCORRECT PASSWORD"
                                else:
                                    RegisteredClients.append((client_name, client_IP, client_UDP_Port, client_Pass))
                                    #Justin Testing
                                    clientSubjects.append([client_name])
                                    message = f"REGISTERED {request_id}"
                                    writeToCSV()

                                    print(client_name, client_Pass)

                                    if not any(((clientPass[0] == client_name)) for clientPass in clientPasswords):
                                        clientPasswords.append((client_name, client_Pass))
                                        handleSendServertoServer("UPDATE-PASSWORD "  +  client_name + " " + client_Pass, waitForAck=False)
                                        writeToPasswordCSV()   
                    else:
                        message = "REFER " + request_id + " " + otherHOST + " " + str(TCPPort) + " " + str(UDPPort)
                        
    return message

def TCPUnregister(request):
    parts = request.split()
    if len(parts) < 3:
        return "UNREGISTER-DENIED: INVALID REQUEST FORMAT"

    message = "NOT REGISTERED"

    client_name = str(parts[2]).lower()
    with stateLock:
        for client in RegisteredClients:
            if (client[0] == client_name):
                RegisteredClients.remove(client)

                #Justin Testing
                message = "UNREGISTERED " + parts[1]

                for subject in clientSubjects:
                    if subject[0] == client_name:
                        clientSubjects.remove(subject)

                writeToCSV()
                break
    return message

def TCPUpdate(request, client_ip):
    parts = request.split()
    message = ""

    if len(parts) < 5:
        message = "UPDATE-DENIED: INVALID REQUEST FORMAT"
    else:
        request_id = parts[1]
        client_name_raw = parts[2]
        client_name = str(client_name_raw).lower()
        new_IP = str(parts[3])
        print("New IP: " + new_IP) 
        new_udp_port = str(parts[4])

        try:
            int(new_udp_port)
        except (TypeError, ValueError):
            return "UPDATE-DENIED " + request_id + " INVALID UDP PORT"
        
        client_password = ""
        client_exists = False

        with stateLock:
            for client in RegisteredClients:
                if (client[0] == client_name):

                    for clientPass in clientPasswords:
                        if clientPass[0] == client_name:
                            client_password = clientPass[1]
                            client_exists = True

                            RegisteredClients.remove(client)
                            RegisteredClients.append((client_name, new_IP, new_udp_port, client_password))
                            writeToCSV()
                    break

        if not client_exists:
            return "UPDATE-DENIED " + request_id + " Name and IP not registered"

        # unregister_message = TCPUnregister("Unregister " + request_id + " " + client_name_raw)
        # if not unregister_message.startswith("UNREGISTERED"):
        #     return "UPDATE-DENIED " + request_id + " UNREGISTER FAILED"

        message = "UPDATE-CONFIRMED " + request_id + " " + client_name_raw + " " + new_IP + " " + new_udp_port
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

    with stateLock:
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

    with stateLock:
        for client in RegisteredClients:
            if (client[0] == client_name):
                RegisteredClients.remove(client)

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

    if parts[0] != "FORWARD":
        serverMessage = "FORWARD " + " ".join(parts[1:])
        handleSendServertoServer(serverMessage, waitForAck=False)
    

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

    if addr is not None:
        udpSock.sendto(
            f"PUBLISH-OK {rq}".encode(),
            addr
        )

    with stateLock:
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
                    print(user_addr)
                    udpSock.sendto(messageToSend.encode(), user_addr) 
                    continue                     
                else:
                    continue

def UDPComment(request, addr):
    parts = request.split()

    if len(parts) < 6:
        if addr is not None:
            udpSock.sendto("COMMENT-DENIED INVALID-FORMAT".encode(), addr)
        return

    if parts[0] != "FORWARD-COMMENT":
        serverMessage = "FORWARD-COMMENT " + " ".join(parts[1:])
        handleSendServertoServer(serverMessage, waitForAck=False)
    

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

    with stateLock:
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
                            continue                    
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
        refresh_state_view()


def getUDPDataFromClient():
    while not serverStopEvent.is_set():
        try:
            data, addr = udpSock.recvfrom(4096)
        except ConnectionResetError:
            # Ignore ICMP Port Unreachable errors on Windows
            continue
        except socket.timeout:
            continue
        except OSError:
            break
        request = data.decode()
        print(f"UDP: {request}")

        parts = request.split()
        if not parts:
            continue
        command = parts[0]

        # Handle UDP server-to-server control messages.
        if command == "S2S-REGISTER":
            if len(parts) >= 3:
                request_id = parts[1]
                client_name = parts[2].lower()
                ack = "ACCEPT" if not is_registered_client(client_name) else "DENY"
                udpSock.sendto(f"S2S-REGISTER-ACK {request_id} {ack}".encode(), addr)
            continue

        if command == "S2S-REGISTER-ACK":
            if len(parts) >= 3:
                request_id = parts[1]
                ack = parts[2]
                with ackCondition:
                    pendingRegisterAcks[request_id] = ack
                    ackCondition.notify_all()
            continue

        if command == "S2S-UPDATE-PASSWORD":
            if len(parts) >= 3:
                client_name = parts[1].lower()
                new_password = parts[2]
                with stateLock:
                    if not any((cp[0] == client_name) for cp in clientPasswords):
                        clientPasswords.append((client_name, new_password))
                        writeToPasswordCSV()
            continue

        processingCommands.append(request)
        updateUserCommands()
        if command == "FORWARD":
             UDPPublish(request, None)
        elif command == "FORWARD-COMMENT":
            UDPComment(request, addr)
        else:
            print(RegisteredClients)
            if is_registered_client(str(parts[2]).lower()):
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
    # UDP-based server-to-server communication using the existing udpSock.
    global udpSock
    otherServerUDPAddress = (otherHOST, UDPPort)
    try:
        if waitForAck:
            parts = message.split()
            if len(parts) < 3:
                return True

            request_id = parts[1] + "-" + str(time.time_ns())
            client_name = parts[2].lower()
            outbound = f"S2S-REGISTER {request_id} {client_name}"

            with ackCondition:
                pendingRegisterAcks.pop(request_id, None)

            udpSock.sendto(outbound.encode(), otherServerUDPAddress)

            deadline = time.time() + 2.0
            with ackCondition:
                while request_id not in pendingRegisterAcks and time.time() < deadline:
                    remaining = deadline - time.time()
                    ackCondition.wait(timeout=max(0.0, remaining))
                ack = pendingRegisterAcks.pop(request_id, None)

            if ack == "ACCEPT":
                return False
            return True

        if message.startswith("UPDATE-PASSWORD "):
            udpSock.sendto(("S2S-UPDATE-PASSWORD " + message[len("UPDATE-PASSWORD "):]).encode(), otherServerUDPAddress)
        else:
            udpSock.sendto(message.encode(), otherServerUDPAddress)
    except Exception as e:
        print(f"Error sending UDP to other server at {otherServerUDPAddress}: {e}")
        if waitForAck:
            return True

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
            elif request == "FORWARD":
                UDPPublish(message, None)
            elif request == "Publish-Comment":
                UDPComment(message, None)
            elif request == "UPDATE-PASSWORD":
                client_name = parts[1].lower()
                new_password = parts[2]
                with stateLock:
                    clientPasswords.append((client_name, new_password))
                    writeToPasswordCSV()
    except Exception as e:
        print(f"Error receiving data from other server: {e}")
    finally:
        connection.close()

# ================= End Server-to-Server Communication Functions =================

def serverAcceptLoop():
    global clientSock
    while not serverStopEvent.is_set():
        try:
            clientConnection, client_address = clientSock.accept()
        except socket.timeout:
            continue
        except OSError:
            break

        handleClientThread = threading.Thread(
            target=getDatafromClient,
            args=(clientConnection, client_address,)
        )
        handleClientThread.daemon = True
        handleClientThread.start()


def close_socket(sock):
    if sock is not None:
        try:
            sock.close()
        except OSError:
            pass


def start_server():
    global clientSock, udpSock
    global udpConnectionThread, serverToServerThread, serverMainThread
    global serverRunning

    if serverRunning:
        return

    if not prompt_startup_configuration():
        print("Server start cancelled: setup was not completed.")
        return

    serverStopEvent.clear()

    try:
        udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udpSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        udpSock.bind((HOST, UDPPort))
        udpSock.settimeout(1.0)

        clientSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        clientSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        clientSock.bind((HOST, TCPPort))

        clientSock.listen(5)
        clientSock.settimeout(1.0)

        if not RegisteredClients and not clientSubjects and not clientPasswords and not processingCommands:
            readCSVInit()

        udpConnectionThread = threading.Thread(target=getUDPDataFromClient, daemon=True)
        udpConnectionThread.start()

        # serverToServerThread = threading.Thread(target=listenServertoServer, daemon=True)
        # serverToServerThread.start()

        serverMainThread = threading.Thread(target=serverAcceptLoop, daemon=True)
        serverMainThread.start()

        serverRunning = True
        print(f"Server started. TCP client port={TCPPort}, TCP s2s port={UDPPort}, UDP port={UDPPort}")
    except Exception as e:
        print(f"Server start failed: {e}")
        stop_server()


def stop_server():
    global clientSock, udpSock
    global serverRunning

    if not serverRunning and clientSock is None and udpSock is None:
        return

    serverStopEvent.set()

    close_socket(clientSock)
    close_socket(udpSock)

    clientSock = None
    udpSock = None
    serverRunning = False
    print("Server stopped.")


def refresh_state_view():
    if root is None or state_widget is None:
        return

    with stateLock:
        registered_snapshot = [tuple(item) for item in RegisteredClients]
        subjects_snapshot = [list(item) for item in clientSubjects]
        publications_snapshot = [tuple(item) for item in availablePublications]
        commands_snapshot = list(processingCommands)

    status_text = (
        f"Status: {'RUNNING' if serverRunning else 'STOPPED'}\n"
        f"Host IP: {HOST}\n"
        f"Server selection: {SERVER_SELECTION}\n"
        f"Other server host: {otherHOST}\n"
        f"Client TCP port: {TCPPort}\n"
        f"Server TCP port: {UDPPort}\n"
        f"UDP port: {UDPPort}\n"
        f"Registered clients: {len(registered_snapshot)}\n"
        f"Subjects entries: {len(subjects_snapshot)}\n"
        f"Tracked publications: {len(publications_snapshot)}\n"
        f"Commands in progress: {len(commands_snapshot)}"
    )

    status_label.config(
        text=status_text,
        fg="green" if serverRunning else "red"
    )

    lines = []
    lines.append("=== Registered Clients ===")
    if registered_snapshot:
        for row in registered_snapshot:
            if len(row) >= 3:
                lines.append(f"- {row[0]} | {row[1]}:{row[2]}")
            else:
                lines.append(f"- {row}")
    else:
        lines.append("(none)")

    lines.append("\n=== Client Subjects ===")
    if subjects_snapshot:
        for row in subjects_snapshot:
            lines.append(f"- {row[0]}: {', '.join(row[1:]) if len(row) > 1 else '(none)'}")
    else:
        lines.append("(none)")

    lines.append("\n=== Publications ===")
    if publications_snapshot:
        for subject, title in publications_snapshot:
            lines.append(f"- {subject} | {title}")
    else:
        lines.append("(none)")

    lines.append("\n=== Processing Commands ===")
    if commands_snapshot:
        for command in commands_snapshot[-20:]:
            lines.append(f"- {command}")
    else:
        lines.append("(none)")

    state_widget.delete("1.0", tk.END)
    state_widget.insert(tk.END, "\n".join(lines))

    root.after(1200, refresh_state_view)


def clear_logs():
    if log_widget is not None:
        log_widget.delete("1.0", tk.END)


def on_close():
    stop_server()
    if root is not None:
        root.destroy()


def setup_ui():
    global root, log_widget, status_label, state_widget

    root = tk.Tk()
    root.title("COEN 366 - News Sharing Server")
    root.geometry("1100x700")

    builtins.print = gui_print

    left_panel = tk.Frame(root, width=260, bg="#f2f5f7")
    left_panel.pack(side="left", fill="y", padx=10, pady=10)
    left_panel.pack_propagate(False)

    right_panel = tk.Frame(root)
    right_panel.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    tk.Label(left_panel, text="Server Controls", font=("Segoe UI", 12, "bold"), bg="#f2f5f7").pack(pady=(10, 8))
    tk.Button(left_panel, text="Start Server", width=20, command=start_server).pack(pady=4)
    tk.Button(left_panel, text="Stop Server", width=20, command=stop_server).pack(pady=4)
    tk.Button(left_panel, text="Refresh State", width=20, command=refresh_state_view).pack(pady=4)
    tk.Button(left_panel, text="Clear Logs", width=20, command=clear_logs).pack(pady=4)
    tk.Button(left_panel, text="Quit", width=20, fg="red", command=on_close).pack(side="bottom", pady=15)

    status_label = tk.Label(left_panel, text="Status: STOPPED", justify="left", anchor="w", bg="#f2f5f7", fg="red")
    status_label.pack(fill="x", pady=(12, 4))

    tk.Label(right_panel, text="Server Logs", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    log_widget = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD, height=16)
    log_widget.pack(fill="both", expand=True, pady=(2, 8))

    tk.Label(right_panel, text="Live Server State", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    state_widget = scrolledtext.ScrolledText(right_panel, wrap=tk.WORD, height=14)
    state_widget.pack(fill="both", expand=True, pady=(2, 2))

    root.protocol("WM_DELETE_WINDOW", on_close)

    start_server()
    refresh_state_view()
    root.mainloop()


if __name__ == "__main__":
    setup_ui()