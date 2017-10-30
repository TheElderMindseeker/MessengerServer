import time
import socket
import threading
from request_handler import request_handler

if __name__ == "__main__":
    HOST, PORT = '', 3549

    server_socket = socket.socket()
    server_socket.bind((HOST, PORT))
    server_socket.listen(2)

    while True:
        time.sleep(1)
        socket, address = server_socket.accept()
        new_thread = threading.Thread(target=request_handler, args=(socket, address))
        new_thread.start()