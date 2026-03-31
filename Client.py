import socket
import sys
import time
import errno
import threading
import random
import tkinter as tk
from tkinter import scrolledtext, simpledialog, messagebox

#function for client selecting which server to send to? or too complicated
randomInt = random.randint(1, 2)
udpHOST = "0.0.0.0"
PORTNo = 9999

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

root = None
log_widget = None

# print function for UI
real_print = print

def gui_print(*args):
    message = " ".join(map(str, args))
    if root and log_widget:
        root.after(0, lambda: log_widget.insert(tk.END, message + "\n"))
        root.after(0, lambda: log_widget.see(tk.END))
    real_print(message)


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

    global server_address
    global registered, request, refered

    try:
        sock.connect(server_address)
        sock.settimeout(3.0)

        sock.sendall(message.encode())
        

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


# functions in the system
def on_register():
    global userName, Request
    name = simpledialog.askstring("Input", "Enter your name:")
    if name:
        userName = name
        message = f"Register {Request} {userName} {clientIP} {PORTNo}"
        threading.Thread(target=sendMessage, args=(message,), daemon=True).start()
        update_request()

def on_publish():
    global Request
    subj = simpledialog.askstring("Publish", "Enter subject:")
    title = simpledialog.askstring("Publish", "Enter title:")
    text = simpledialog.askstring("Publish", "Enter text:")
    if subj and title and text:
        message = f"Publish {Request} {userName} Subj3ct:{subj}* Titl3:{title}* T3xt: {text}"
        startUDP(PORTNo, "Sender", message)
        update_request()

def on_subjects():
    global Request
    subjects = simpledialog.askstring("Subjects", "Enter subjects (comma separated):")
    if subjects:
        message = f"Subjects {Request} {userName} {subjects}"
        threading.Thread(target=sendMessage, args=(message,), daemon=True).start()
        update_request()

def on_unregister():
    global Request
    if messagebox.askyesno("Unregister", f"Do you want to unregister user: {userName}?"):
        message = f"Unregister {Request} {userName}"
        threading.Thread(target=sendMessage, args=(message,), daemon=True).start()
        update_request()

def update_request():
    global Request
    Request += 1

def on_update():
    global Request
    new_port = simpledialog.askstring("Update", "Enter new UDP port:")
    if new_port:
        message = f"Update {Request} {userName} {new_port}"
        threading.Thread(target=sendMessage, args=(message,), daemon=True).start()
        update_request()

def update_status_label():
    if registered:
        status_label.config(text="Status: Registered", fg="green")
    else:
        status_label.config(text="Status: Unregistered", fg="red")
    root.after(1000, update_status_label)

def on_quit():
    if messagebox.askokcancel("Quit", "Do you want to quit and notify server?"):
        msg = f"Quit {Request} {userName}"
        threading.Thread(target=sendMessage, args=(msg,), daemon=True).start()
        time.sleep(0.5)
        root.destroy()


# UI starter
def setup_ui():
    global root, log_widget, print
    root = tk.Tk()
    root.title("COEN 366 - Network Client")
    root.geometry("800x600")

    
    frame_left = tk.Frame(root, width=200, bg="#f0f0f0")
    frame_left.pack(side="left", fill="y", padx=10, pady=10)

    
    log_widget = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60)
    log_widget.pack(side="right", expand=True, fill="both", padx=10, pady=10)

    
    import builtins
    builtins.print = gui_print 

   
    tk.Label(frame_left, text="Actions", font=("Arial", 12, "bold")).pack(pady=10)
    tk.Button(frame_left, text="Register", width=15, command=on_register).pack(pady=5)
    tk.Button(frame_left, text="Subscribe", width=15, command=on_subjects).pack(pady=5)
    tk.Button(frame_left, text="Update Port", width=15, command=lambda: threading.Thread(target=on_update).start()).pack(pady=5)
    tk.Button(frame_left, text="Publish (UDP)", width=15, command=on_publish).pack(pady=5)
    tk.Button(frame_left, text="Unregister", width=15, command=lambda: threading.Thread(target=lambda: sendMessage(f"Unregister {Request} {userName}")).start()).pack(pady=5)
    
    tk.Button(frame_left, text="Quit", width=15, fg="red", command=root.destroy).pack(side="bottom", pady=20)

    
    startUDP(PORTNo, "Listener", "")
    
    root.mainloop()
    stopUDP() 

if __name__ == "__main__":
    setup_ui()

