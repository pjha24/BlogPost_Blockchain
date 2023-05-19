import blockchain
import os
import socket
import time
import sys
import threading



other_processes = []
block = None

def post(username, title, content):
  global block
  block = blockchain.post(block, username,title,content)
  print("Post Successful")

def comment(username, title, content):
  global block
  block = blockchain.comment(block, username,title,content)
  print("Comment Successful")

def handle_input():
  while True:
    try:
        transaction = input().split("  ")
        if(transaction[0] == "post"):
            post(transaction[1], transaction[2], transaction[3])
        elif(transaction[0] == "comment"):
            comment(transaction[1], transaction[2], transaction[3])
        elif(transaction[0] == "view all"):
            print("[" + ",".join(blockchain.viewAll(block)) + "]")
        elif(transaction[0] == "view posts"):
            print("[" + ",".join(blockchain.viewUser(block, transaction[1])) + "]")
        elif(transaction[0] == "view comments"):
            print("[" + ",".join(blockchain.viewComments(block, transaction[1])) + "]")
        elif(transaction[0] == "debug"):
            print("[" + ",".join(blockchain.debug(block)) + "]")
        elif(transaction[0] == "broadcast"):
            for conn in other_processes:                #iterating through all other process
                send_message(conn, transaction[1])
        elif(transaction[0] == "exit"):
            sys.stdout.flush()
            for conn in other_processes:
                conn.close()
            os._exit(0)
        else:
            print("Invalid command")
    except:
      print("Invalid command")

#connecting to hopefully existing port
def process_conn(port):
    print(f"in process of connecting {port}")
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((socket.gethostname(), port))
            other_processes.append(s)
            break
        except:
            time.sleep(5)
    # print(f"Connected by {addr}", flush=True)
    print(f"connected to port {port}", flush=True)
    


def process_transaction(sock, port, data ):
    print(f"received {data} from {port}")

def process_bind(self_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((socket.gethostname(), self_port))
        s.listen()
        print("binded bro")
        while True:
            try:
                conn, addr = s.accept()
            except:
                print("exception in accept", flush=True)
                break
            threading.Thread(target=listening, args=(conn,addr)).start()

def listening(conn,addr):
    print(f"connected to {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if(len(data) == 0):
                break
        except:
            print(f"exception receiving data from {addr[1]}", flush=True)
            break
        threading.Thread(target=process_transaction, args=(conn, addr, data)).start()

def send_message(sock, data):
    try:
        sock.sendall(bytes(data , "utf-8"))
    except:
        print("Error sending message", flush=True)
    return


if __name__ == "__main__":
    threading.Thread(target=process_bind, args=(int(sys.argv[1]),)).start()
    for other_port in sys.argv[2:]:
        process_conn(int(other_port))
    handle_input()

