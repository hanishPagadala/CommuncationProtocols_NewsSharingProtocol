import socket
import sys
import time
import errno
import threading

udpHOST = "0.0.0.0"
PORTNo = 8889

serverAddress = "localhost" #'132.205.94.193'
udpServerPort = 8888

# try:
#     udpSock.bind((udpHOST, PORTNo))
# except socket.error as msg:
#     print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
#     sys.exit()

Request = 0
Name = "Lebron"
clientIP = socket.gethostbyname(socket.gethostname())
server_address = (serverAddress, 10000)
#server_address = ('132.205.46.76', 10000)

udpListenerSock = None
udpListenerThread = None
udpListenerStopEvent = threading.Event()


def udpListenerLoop(sock):
    while not udpListenerStopEvent.is_set():
        try:
            data, addr = sock.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError:
            break

        if not data:
            continue

        reply = data.decode(errors="replace")
        print(f"\n[UDP] {reply} from {addr}")


def stopUDPListener():
    global udpListenerSock
    global udpListenerThread

    udpListenerStopEvent.set()

    if udpListenerSock is not None:
        try:
            udpListenerSock.close()
        except OSError:
            pass
        udpListenerSock = None

    if udpListenerThread is not None and udpListenerThread.is_alive():
        udpListenerThread.join(timeout=1.5)
    udpListenerThread = None


def startUDPListener(port):
    global udpListenerSock
    global udpListenerThread

    stopUDPListener()
    udpListenerStopEvent.clear()

    listener = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((udpHOST, int(port)))
    listener.settimeout(1.0)

    udpListenerSock = listener
    udpListenerThread = threading.Thread(target=udpListenerLoop, args=(listener,), daemon=True)
    udpListenerThread.start()
    print(f"UDP listener started on {udpHOST}:{port}")

def sendMessage(message):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    print("Connected to server at", server_address)

    sock.sendall(message.encode())
    print("Sending Message to Server")

    recieved = ""
    data = sock.recv(1024)
    if data:
        recieved += data.decode()
        print("Received:", recieved)
        reply = recieved.split()
        if reply[0] == "UPDATE-CONFIRMED":
            global PORTNo
            PORTNo = int(reply[4])
            startUDPListener(PORTNo)


    print("no more info to receive from the server at", server_address)
    sock.close()
    time.sleep(0.2)

def sendUDPMessage(message, local_port):
    # Use a short-lived UDP socket to send publish command and await ACK.
    # Incoming publishes are handled by the background listener on PORTNo.
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        udpSock.settimeout(3)
        udpSock.sendto(message.encode(), (serverAddress, udpServerPort))
        print(f"Sending Message to Server UDP on port {local_port}")

        try:
            data = udpSock.recvfrom(4096)
            reply = data[0].decode()
            addr = data[1]
            print("Received:", reply, "from", addr)
        except socket.timeout:
            print("No UDP acknowledgement received from server")
    finally:
        udpSock.close()

try:
    startUDPListener(PORTNo)
    while True:
        time.sleep(0.1) 
        message = ""
        userAction = input("Choose an Action: Register | Unregister | Update | Subjects | Publish | Comment | Quit: ")
        userAction = userAction.lower()
        messageType = ""
        if (userAction == "register"):

            userName = input("Enter your name: ")
            message = "Register " + str(Request) + " " + userName + " " + clientIP + " " + str(PORTNo)
            messageType = "TCP"

        elif userAction == "unregister":

            userName = input("Enter your name: ")
            message = "Unregister " + str(Request) + " " + userName
            messageType = "TCP"

        elif userAction == "update":

            userName = input("Enter your name: ")
            newPort = input("Enter your new UDP port: ")
            message = "Update " + str(Request) + " " + userName + " " + newPort
            messageType = "TCP"

        elif userAction == "subjects":
            
            userName = input("Enter your name: ")
            listOfSubjects = input("Enter the subjects you want to subscribe to (comma separated separated): ")
            message = "Subjects " + str(Request) + " " + userName + " " + listOfSubjects
            messageType = "TCP"

        elif userAction == "comment":

            userName = input("Enter your name: ")
            listOfSubjects = input("Enter the subject you wish to publish: ")
            subjectTitle = input("Enter the title of your publication: ")
            subjectText = input("Enter your comment: ")
            message = "Subjects " + str(Request) + " " + userName + " " + listOfSubjects + " " + subjectTitle + " " + subjectText
            messageType = "TCP"

        elif userAction == "quit":

            message = "Quit"
            messageType = "TCP"

        elif userAction == "publish":

            userName = input("Enter your name: ")
            userSubject = input("Enter the subject you wish to publish: ")
            subjectTitle = input("Enter the title of your publication: ")
            subjectText = input("Enter the text of your publication: ")
            message = "Publish " + str(Request) + " " + userName + " "+ userSubject + " Titl3:" + subjectTitle + " T3xt:" + subjectText
            messageType = "UDP"

        else:
            message = "Penis"
            messageType = "TCP"
        
        if messageType == "TCP":
            tcpThread = threading.Thread(target=sendMessage, args=(message, )) 
            tcpThread.start()
            tcpThread.join()
        elif messageType == "UDP":
            udpThread = threading.Thread(target=sendUDPMessage, args=(message, PORTNo, )) 
            udpThread.start()
            udpThread.join()
    
        if userAction == "quit":
            break
        Request += 1
finally:
    stopUDPListener()
    time.sleep(0.5)
