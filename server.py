import blockchain
import os
import socket
import time
import sys
import threading

# Multi Paxos Definitions:

# (ballot, pid, depth)
ballotNum = [0,0,0]
acceptNum = [0,0,0]

acceptVal = ""

curLeader = None

promises = []
accepts = 0

HOST = "127.0.0.1"
pid = None

other_processes = {}
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
            threading.Thread(target=propose, args=("~".join(transaction),)).start()
        elif(transaction[0] == "comment"):
            threading.Thread(target=propose, args=("~".join(transaction),)).start()
        elif(transaction[0] == "view all"):
            print("[" + ",".join(blockchain.viewAll(block)) + "]")
        elif(transaction[0] == "view posts"):
            print("[" + ",".join(blockchain.viewUser(block, transaction[1])) + "]")
        elif(transaction[0] == "view comments"):
            print("[" + ",".join(blockchain.viewComments(block, transaction[1])) + "]")
        elif(transaction[0] == "debug"):
            print("[" + ",".join(blockchain.debug(block)) + "]")
        elif(transaction[0] == "broadcast"):
            for _, conn in other_processes.items():                #iterating through all other process
                send_message(conn, transaction[1])
        elif(transaction[0] == "exit"):
            sys.stdout.flush()
            for _, conn in other_processes.items():
                conn.close()
            os._exit(0)
        else:
            print("Invalid command")
    except:
      print("Invalid command")

def decode(tuple_val):
    return [int(i) for i in tuple_val[1:-1].split(",")]

def greater(b1, b2):
    if(b1[2] > b2[2]):
        return True
    if(b1[2] < b2[2]):
        return False
    return b1[0] > b2[0] or (b1[0] == b2[0] and b1[1] > b2[1])

def execute(transaction):
    transaction = transaction.split("~")
    if(transaction[0] == "post"):
        post(transaction[1], transaction[2], transaction[3])
    elif(transaction[0] == "comment"):
        comment(transaction[1], transaction[2], transaction[3])

def elect_leader(curBallotNum):
    global promises, curLeader
    promises = []
    for _,sock in other_processes.items():
        send_message(sock, f"prepare|{ballotNum}")
    while len(promises) < 3 and curBallotNum == ballotNum:
        print("waiting for promises")
        time.sleep(7)
    if curBallotNum == ballotNum:
        curLeader = pid

def phase23(curBallotNum, value):
    global accepts
    if curBallotNum == ballotNum:
        proposed_value = value
        highest_num = (0,0,0)
        for accept_num, accept_value in promises:           #phase 2
            if greater(accept_num, highest_num):
                highest_num = accept_num
                proposed_value = accept_value
        accepts = 0
        for _,sock in other_processes.items():
            send_message(sock, f"accept|{ballotNum}|{proposed_value}")
    
    while accepts < 3 and curBallotNum == ballotNum:
        print("waiting for accepts")
        time.sleep(7)
    if curBallotNum == ballotNum:                       #phase 3
        execute(value)
        for _,sock in other_processes.items():
            send_message(sock, f"decide|{value}")


def propose(value):
    global curBallotNum
    if curLeader is None:                                   #starting leader election
        ballotNum[0] += 1
        ballotNum[1] = pid
        curBallotNum = ballotNum
        elect_leader(curBallotNum)
        phase23(curBallotNum, value)
    elif curLeader == pid:
        ballotNum[0] += 1
        ballotNum[1] = pid
        curBallotNum = ballotNum
        phase23(curBallotNum, value)
    else:
        send_message(other_processes[curLeader], f"value|{value}")

        

#connecting to hopefully existing port
def process_conn(port):
    print(f"in process of connecting {port}")
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((HOST, port))
            other_processes[port] = s
            break
        except:
            time.sleep(5)
    # print(f"Connected by {addr}", flush=True)
    print(f"connected to port {port}", flush=True)
    


def process_transaction(sock, port, data ):
    time.sleep(3)
    global acceptNum, acceptVal, ballotNum, accepts, curLeader
    print(f"received {data} from {port}")
    message = data.decode().split("|")
    if message[0] == "prepare":
        b_num = decode(message[1])
        if greater(b_num, ballotNum):
            curLeader = b_num[1]
            ballotNum = b_num
            send_message(other_processes[b_num[1]], f"promise|{b_num}|{acceptNum}|{acceptVal}")
    elif message[0] == "promise":
        b_num = decode(message[1])
        if b_num == ballotNum:
            a_num = decode(message[2])
            promises.append((a_num, message[3]))
    elif message[0] == "accept":
        b_num = decode(message[1])
        if greater(b_num, ballotNum) or b_num == ballotNum:
            ballotNum = b_num
            acceptNum = b_num
            acceptVal = message[2]
            send_message(other_processes[b_num[1]], f"accepted|{b_num}")
    elif message[0] == "accepted":
        b_num = decode(message[1])
        if b_num == ballotNum:
            accepts += 1
    elif message[0] == "decide":
        execute(message[1])
        acceptNum = [0,0,0]
        acceptVal = ""
    elif message[0] == "value":
        threading.Thread(target=propose, args=(message[1],)).start()

        

def process_bind(self_port):
    global pid
    pid = self_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, self_port))
        s.listen()
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

