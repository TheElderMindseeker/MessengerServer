import socket
import threading
from sys import argv
from getopt import gnu_getopt
from request_handler import request_handler

if __name__ == "__main__":
    optlist, args = gnu_getopt(argv[1:], 'n:', ['noise='])

    noise_level = 0.0
    for opt in optlist:
        if opt[0] == '-n':
            noise_level = float(opt[1])
        elif opt[0] == '--noise':
            noise_level = float(opt[1])

    HOST, PORT = '', 3549

    server_socket = socket.socket()
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    server_socket.setblocking(True)

    while True:
        socket, address = server_socket.accept()
        socket.setblocking(True)
        new_thread = threading.Thread(target=request_handler, args=(socket, address, noise_level))
        new_thread.start()