def request_handler(sock, addr):
    while True:
        request = recv_from_socket(sock)
        if request == 'Hello':
            send_by_socket(sock, 'Hi!', addr)
        elif request == 'Bye':
            send_by_socket(sock, 'Bye!', addr)
            break
        else:
            send_by_socket(sock, 'I don\'t understand you\0', addr)
    sock.close()


def send_by_socket(socket, string, address=None):
    if address is None:
        socket.sendall(bytes(string + '\0', 'ascii'))
    else:
        socket.sendto(bytes(string + '\0', 'ascii'), address)


def issue_error_message(socket, error, address=None):
    if address is None:
        socket.sendall(bytes('Error;' + error + '\0', 'ascii'))
    else:
        socket.sendto(bytes('Error;' + error + '\0', 'ascii'), address)


def recv_from_socket(socket, address=None):
    buffer = b''
    while str(buffer, 'ascii').find('\0') == -1:
        if address is None:
            buffer += socket.recv(1024)
        else:
            bs, addr = socket.recvfrom(1024)
            if addr != address:
                raise ValueError

    s = str(buffer, 'ascii')
    s = s[:s.find('\0')]

    return s