import socket

if __name__ == '__main__':
    HOST, PORT = 'localhost', 3549

    client = socket.socket()
    client.connect((HOST, PORT))
    client.sendall(bytes("Hello\0", 'ascii'))
    response = str(client.recv(1024), 'ascii').strip()
    print("Received: {}".format(response))
    client.sendall(bytes("Bye\0", 'ascii'))
    response = str(client.recv(1024), 'ascii').strip()
    print("Received: {}".format(response))
    client.close()