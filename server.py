import blockchain
import os
import socket
import time
import sys
import threading
import copy
import queue

# Multi Paxos Definitions:

# (ballot, pid, depth)
ballotNum = [0,0,0]
acceptNum = [0,0,0]

acceptVal = ""

curLeader = None
leaderQueue = queue.Queue()
isRunning = False

promises = []
accepts = 0


waitingForLeader = False

HOST = "127.0.0.1"
pid = None

other_processes = {}
block = None

def filename():
    return f"{pid}.txt"

def removeTentative():
    if os.path.exists(filename()):
        with open(filename(), "r") as f:
            lines = f.readlines()
            if len(lines) > 0 and lines[-1][-1] == "`":
                with open(filename(), "w") as f:
                    f.writelines(lines[:-1])

def addBlock(additionalBlock, realAdd=True):
    global block
    block = blockchain.construct(additionalBlock, block)
    if realAdd:
        removeTentative()
        with open(filename(), 'a') as f:
            f.write(additionalBlock + "\n")
        if block.T[0] == "post":
            print(f"NEW POST {block.T[2]} from {block.T[1]}")
        if block.T[0] == "comment":
            print(f"NEW COMMENT on {block.T[2]} from {block.T[1]}")


def post(username, title, content):
    return blockchain.post(block, username,title,content)

def comment(username, title, content):
  return blockchain.comment(block, username,title,content)

def exit():
    sys.stdout.flush()
    for _, conn in other_processes.items():
        try:
            conn.close()
        except:
            pass
    os._exit(0)

def handle_input():

  while True:
    try:
        transaction = input().split("  ")
        if(transaction[0] == "post"):
            if blockchain.inBlockchain(block, transaction[2]):
                print("DUPLICATE TITLE")
                continue
            tmp_block = post(transaction[1], transaction[2], transaction[3])
            threading.Thread(target=propose, args=(tmp_block.toString(),)).start()
        elif(transaction[0] == "comment"):
            tmp_block = comment(transaction[1], transaction[2], transaction[3])
            threading.Thread(target=propose, args=(tmp_block.toString(),)).start()
        elif(transaction[0] == "view all"):
            print("[" + ",".join(blockchain.viewAll(block)) + "]")
        elif(transaction[0] == "view"):
            posts = blockchain.viewUser(block, transaction[1])
            if(len(posts) > 0):
                print("[" + ",".join(posts) + "]")
            else:
                print("NO POST")
        elif(transaction[0] == "view comments"):
            print("[" + ",".join(blockchain.viewComments(block, transaction[1])) + "]")
        elif(transaction[0] == "blog"):
            blog = blockchain.blog(block)
            if len(blog) > 0:
                print("[" + ",".join(blog) + "]")
            else:
                print("BLOG EMPTY")
        elif(transaction[0] == "read"):
            print(blockchain.read(block, transaction[1], []))
        elif(transaction[0] == "debug"):
            print("[" + ",".join(blockchain.debug(block)) + "]")
        elif(transaction[0] == "broadcast"):
            for _, conn in other_processes.items():                #iterating through all other process
                send_message(conn, transaction[1])
        elif(transaction[0] == "failLink"):
            send_message(other_processes[int(transaction[1])], f"fail|{pid}")
            other_processes[int(transaction[1])] = None
        elif(transaction[0] == "fixLink"):
            process_conn(int(transaction[1]))
            send_message(other_processes[int(transaction[1])], f"fix|{pid}")
        elif(transaction[0] == "crash"):
            exit()
        elif(transaction[0] == "exit all"):
            for _, conn in other_processes.items():
                send_message(conn, "exit")
            if os.path.exists(filename()):
                os.remove(filename())
            exit()
        elif(transaction[0] == "leader"):
            print(curLeader)
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

def execute(block):
    addBlock(block)

def elect_leader(curBallotNum):
    global promises, curLeader
    promises = []
    print(f"BROADCASTING PREPARE {curBallotNum}")
    for _,sock in other_processes.items():
        send_message(sock, f"prepare|{ballotNum}")
    while len(promises) < 2 and curBallotNum == ballotNum:
        # print("waiting for promises")
        time.sleep(7)
    if curBallotNum == ballotNum:
        curLeader = pid

def phase23(curBallotNum, value):
    global accepts
    if curBallotNum == ballotNum:
        proposed_value = value
        highest_num = (0,0,ballotNum[2])
        for accept_num, accept_value in promises:           #phase 2
            if greater(accept_num, highest_num):
                highest_num = accept_num
                proposed_value = accept_value
        accepts = 0
        with open(filename(), 'a') as f:
            f.write(f"{curBallotNum}|{proposed_value}`")
        print(f"BROADCASTING ACCEPT {curBallotNum}")
        for _,sock in other_processes.items():
            send_message(sock, f"accept|{curBallotNum}|{proposed_value}")
    
        while accepts < 2 and curBallotNum == ballotNum:
            # print("waiting for accepts")
            time.sleep(7)
        if curBallotNum == ballotNum:                       #phase 3
            removeTentative()
            execute(proposed_value)
            print(f"BROADCASTING DECIDE {curBallotNum}")
            for _,sock in other_processes.items():
                send_message(sock, f"decide|{curBallotNum}|{proposed_value}|{pid}")


def getNewBallotNumber():
    ballotNum[0] += 1
    ballotNum[1] = pid
    ballotNum[2] = blockchain.depth(block) + 1

def full_leader_election(value):
    getNewBallotNumber()
    curBallotNum = copy.copy(ballotNum)
    elect_leader(curBallotNum)
    phase23(curBallotNum, value)

def multi_time(value):
    global isRunning
    isRunning = True
    getNewBallotNumber()
    curBallotNum = copy.copy(ballotNum)
    phase23(curBallotNum, value)

def propose(value):
    global ballotNum, isRunning,waitingForLeader
    if curLeader is None:                                   #starting leader election
        full_leader_election(value)
    elif curLeader == pid:
        if isRunning:
            leaderQueue.put(value)
        else:
            multi_time(value)
            while not leaderQueue.empty():
                time.sleep(1)
                value = leaderQueue.get()
                multi_time(value)
            isRunning = False

    else:
        send_message(other_processes[curLeader], f"value|{value}")
        waitingForLeader = True
        count = 0
        while waitingForLeader and count < 4:
            count += 1
            time.sleep(5)
        if waitingForLeader:
            print("TIMEOUT")
            full_leader_election(value)

        

#connecting to hopefully existing port
def process_conn(port):
    # print(f"in process of connecting {port}")
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((HOST, port))
            other_processes[port] = s
            return s
        except:
            return None
    


def process_transaction(sock, port, data ):
    time.sleep(3)
    global acceptNum, acceptVal, ballotNum, accepts, curLeader, waitingForLeader
    # print(f"received {data} from {port}")
    message = data.decode().split("|")
    if message[0] == "prepare":
        b_num = decode(message[1])
        print(f"RECEIVED PREPARE {b_num}")
        if greater(b_num, ballotNum):
            ballotNum = b_num
            print(f"PROMISE {b_num},{acceptNum},{acceptVal}")
            send_message(other_processes[b_num[1]], f"promise|{b_num}|{acceptNum}|{acceptVal}")
    elif message[0] == "promise":
        b_num = decode(message[1])
        print(f"RECEIVED PROMISE {b_num}")
        if b_num == ballotNum:
            a_num = decode(message[2])
            promises.append((a_num, message[3]))
    elif message[0] == "accept":
        b_num = decode(message[1])
        print(f"RECEIVED ACCEPT {b_num}")
        if greater(b_num, ballotNum) or b_num == ballotNum:
            ballotNum = b_num
            acceptNum = b_num
            removeTentative()
            with open(filename(), 'a') as f:
                f.write(f"{acceptNum}|{message[2]}`")
            acceptVal = message[2]
            print(f"ACCEPTED {b_num}")
            send_message(other_processes[b_num[1]], f"accepted|{b_num}")
    elif message[0] == "accepted":
        b_num = decode(message[1])
        print(f"RECEIVED ACCEPTED {b_num}")
        if b_num == ballotNum:
            accepts += 1
    elif message[0] == "decide":
        b_num = decode(message[1])
        print(f"RECEIVED DECIDE {b_num}")
        waitingForLeader = False
        execute(message[2])
        curLeader = int(message[3])
        acceptNum = [0,0,0]
        acceptVal = ""
    elif message[0] == "value":
        threading.Thread(target=propose, args=(message[1],)).start()
    elif message[0] == "reconnect":
        process_conn(int(message[1]))
    elif message[0] == "fail":
        other_processes[int(message[1])] = None
    elif message[0] == "fix":
        process_conn(int(message[1]))
    elif message[0] == "exit":
        os.remove(filename())
        exit()

        

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
                # print("exception in accept", flush=True)
                break
            threading.Thread(target=listening, args=(conn,addr)).start()

def listening(conn,addr):
    # print(f"connected to {addr}")
    while True:
        try:
            data = conn.recv(1024)
            if(len(data) == 0):
                break
        except:
            # print(f"exception receiving data from {addr[1]}", flush=True)
            break
        threading.Thread(target=process_transaction, args=(conn, addr, data)).start()

def send_message(sock, data):
    try:
        sock.sendall(bytes(data , "utf-8"))
    except:
        return


if __name__ == "__main__":
    threading.Thread(target=process_bind, args=(int(sys.argv[1]),)).start()
    if os.path.exists(filename()):
        print("LOADING FROM FILE")
        with open(filename(), "r+") as f:
            lines = f.readlines()
            for line in lines:
                if line[-1] != "`":
                    addBlock(line, False)
                else:
                    vals = line.split("|")
                    acceptNum = [int(i) for i in vals[0][1:-1].split(",")]
                    acceptVal = vals[1][:-1]
    removeTentative()

                
    for other_port in sys.argv[2:]:
        s = process_conn(int(other_port))
        send_message(s, f"reconnect|{int(sys.argv[1])}")
    handle_input()

