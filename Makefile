compile:

server1:
	python3 -u server.py 9001 9002 9003 9004 9005
server2:
	python3 -u server.py 9002 9001 9003 9004 9005
server3:
	python3 -u server.py 9003 9002 9001 9004 9005
server4:
	python3 -u server.py 9004 9002 9003 9001 9005
server5:
	python3 -u server.py 9005 9002 9003 9004 9001