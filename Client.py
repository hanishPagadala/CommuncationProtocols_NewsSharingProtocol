import socket
import sys
import time
import errno
import threading
import random

#function for client selecting which server to send to? or too complicated
randomInt = random.randint(1, 2)
udpHOST = "0.0.0.0"
PORTNo = 8889

serverAddress = "localhost" #'132.205.94.193'
udpServerPort = 8888 if randomInt == 1 else 8889



# try:
#     udpSock.bind((udpHOST, PORTNo))
# except socket.error as msg:
#     print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
#     sys.exit()

Request = 0
userName = "Lebron"
registered = False
refered = False
clientIP = socket.gethostbyname(socket.gethostname())
server_address = (serverAddress, 10000) if randomInt == 1 else (serverAddress, 10001)
#server_address = ('132.205.46.76', 10000)

udpSock = None
udpThread = None
udpStopEvent = threading.Event()


def udpListenerLoop(sock):
    while not udpStopEvent.is_set():
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

def stopUDP():
    global udpSock
    global udpThread

    udpStopEvent.set()

    if udpSock is not None:
        try:
            udpSock.close()
        except OSError:
            pass
        udpSock = None

    current = threading.current_thread()
    if udpThread is not None and udpThread.is_alive() and udpThread is not current:
        udpThread.join(timeout=0.05)
    udpThread = None

def startUDP(port, mode: str, message: str):
    if not mode:
        mode = "Listener"

    global udpSock
    global udpThread

    stopUDP()       # If there is already a present one, cut it off (update command)
    udpStopEvent.clear()

    time.sleep(0.1) # Give the previous thread a moment to close

    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udpSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udpSock.bind((udpHOST, int(port)))
    udpSock.settimeout(1.0)

    if mode == "Listener":
        udpThread = threading.Thread(target = udpListenerLoop, args=(udpSock,), daemon=True)
        udpThread.start()
    else:
        udpThread = threading.Thread(target = sendUDPMessage, args=(udpSock, message, int(port)), daemon=True)
        udpThread.start()
        

def sendUDPMessage(sock, message, port):
    # Regular send and recieve UDP Messages, closes after each message
    try:
        sock.sendto(message.encode(), (serverAddress, udpServerPort))

        try:
            data = sock.recvfrom(4096)
            reply = data[0].decode()
            addr = data[1]
            print("Received:", reply, "from", addr)
        except socket.timeout:
            print("No UDP acknowledgement received from server")
    finally:
        stopUDP()
        startUDP(port, "Listener", "")

def sendMessage(message):
    #TCP send and recieve, closes after each message
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    reply = ""
    global server_address

    reply = ""
    global server_address

    try:
        sock.connect(server_address)
        sock.settimeout(3.0)

        sock.sendall(message.encode())
        global registered, Request, refered
        global registered, Request, refered

        data = sock.recv(4096)
        recieved = ""
        recieved = ""
        if data:
            recieved += data.decode()
            print("Received:", recieved)
            reply = recieved.split()
            if reply[0] == "UPDATE-CONFIRMED":
                global PORTNo
                PORTNo = int(reply[4])
                startUDP(PORTNo, "Listener", "")
            elif reply[0] == "REGISTERED":
                registered = True
                refered = False
            elif reply[0] == "UNREGISTERED":
                registered = False
                Request = 0
            elif reply[0] == "REFER":
                print("You are being referred to another server.")
                registered = False
                refered = True
                Request = 0

            elif reply[0] == "REFER":
                print("You are being referred to another server.")
                registered = False
                refered = True
                Request = 0

            if (len(reply) > 4) and(reply[3] == "ALREADY") and (reply[4] == "REGISTERED"):
                print("Registration denied: You are already registered. Please update your information or unregister first.")
                registered = True

    except socket.timeout:
        print("No response received from server within timeout period.")
    except ConnectionRefusedError:
        print("Connection refused by the server. Please ensure the server is running and reachable.")

    sock.close()
    time.sleep(0.2)
    if (refered) and (len(reply) > 3):
        newMessage = "Register " + str(Request) + " " + userName + " " + clientIP + " " + str(PORTNo)
        server_address = (reply[2], int(reply[3]))
        sendMessage(newMessage)
        refered = False


try:
    startUDP(PORTNo, "Listener", "")
    while True:
        time.sleep(0.05) 
        message = ""
        messageType = ""

        if not registered:
            userAction = input("Choose an Action: Register | Quit: ")
            userAction = userAction.lower()

            if (userAction == "register"):
                if registered:
                    print("You are already registered. Please update your information or unregister first.")
                    continue
                else:
                    userName = input("Enter your name: ")
                    message = "Register " + str(Request) + " " + userName + " " + clientIP + " " + str(PORTNo)
                    messageType = "TCP"
            elif userAction == "quit":
                message = "Quit " + str(Request) + " " + userName
                messageType = "TCP"
        else:
            userAction = input("Choose an Action: Update | Subjects | Publish | Comment | Unregister | Quit: ")
            userAction = userAction.lower()

            if (userAction == "register"):
                if registered:
                    print("You are already registered. Please update your information or unregister first.")
                    continue
                else:
                    userName = input("Enter your name: ")
                    message = "Register " + str(Request) + " " + userName + " " + clientIP + " " + str(PORTNo)
                    messageType = "TCP"

            elif userAction == "unregister":

                if not registered:
                    print("You are not registered.")
                    continue
                else:
                    message = "Unregister " + str(Request) + " " + userName
                    messageType = "TCP"

            elif userAction == "update":

                newPort = input("Enter your new UDP port: ")
                message = "Update " + str(Request) + " " + userName + " " + newPort
                messageType = "TCP"

            elif userAction == "subjects":
                
                listOfSubjects = input("Enter the subjects you want to subscribe to (comma separated separated): ")
                message = "Subjects " + str(Request) + " " + userName + " " + listOfSubjects
                messageType = "TCP"

            elif userAction == "comment":

                subject = input("Enter the subject you wish to publish: ")
                subjectTitle = input("Enter the title of your publication: ")
                subjectText = input("Enter your comment: ")
                message = "Publish-Comment " + str(Request) + " " + userName + " " + subject + "* " + subjectTitle + "* " + subjectText
                messageType = "UDP"

            elif userAction == "quit":

                message = "Quit " + str(Request) + " " + userName
                messageType = "TCP"

            elif userAction == "publish":

                userSubject = input("Enter the subject you wish to publish: ")
                subjectTitle = input("Enter the title of your publication: ")
                subjectText = input("Enter the text of your publication: ")
                message = "Publish " + str(Request) + " " + userName + " Subj3ct:"+ userSubject + "* Titl3:" + subjectTitle + "* T3xt: " + subjectText
                messageType = "UDP"

            else:

                message = "Penis"
                messageType = "TCP"
        
        if messageType == "TCP":
            tcpThread = threading.Thread(target=sendMessage, args=(message, )) 
            tcpThread.start()
            tcpThread.join()
        elif messageType == "UDP":
            startUDP(PORTNo, "Sender", message)
            # udpThread = threading.Thread(target=sendUDPMessage, args=(message, PORTNo, )) 
            # udpThread.start()
            # udpThread.join()
    
        if userAction == "quit":
            break
        Request += 1
finally:
    stopUDP()
