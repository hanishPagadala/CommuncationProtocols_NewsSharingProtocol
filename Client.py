import socket
import sys
import time
import errno
import threading

udpHOST = "0.0.0.0"
PORTNo = 8889

udpServerHost = 'localhost'
udpServerPort = 8888

try:
    udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
except socket.error as msg:
    print('Failed to create socket. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
    sys.exit()
# try:
#     udpSock.bind((udpHOST, PORTNo))
# except socket.error as msg:
#     print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
#     sys.exit()

Request = 0
Name = "Lebron"
clientIP = socket.gethostbyname(socket.gethostname())
server_address = ('localhost', 10000)
#server_address = ('132.205.46.76', 10000)

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

    print("no more info to receive from the server at", server_address)
    sock.close()
    time.sleep(0.2)

def sendUDPMessage(message):
    udpSock.sendto(message.encode(), (udpServerHost, udpServerPort))
    print("Sending Message to Server UDP")

    data = udpSock.recvfrom(4096)
    reply = data[0].decode()
    addr = data[1]

    print("Received:", reply, "from", addr)
    time.sleep(0.2)

try:
    while True:
        time.sleep(0.1) 
        message = ""
        userAction = input("Choose an Action: Register | Unregister | Update | Subjects | Publish | Quit: ")
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
            listOfSubjects = input("Enter the subjects you want to subscribe to (space separated): ")
            message = "Subjects " + str(Request) + " " + userName + " " + listOfSubjects
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
            udpThread = threading.Thread(target=sendUDPMessage, args=(message, )) 
            udpThread.start()
            udpThread.join()
    
        if userAction == "quit":
            break
        Request += 1
finally:
    time.sleep(0.5)
    udpSock.close()