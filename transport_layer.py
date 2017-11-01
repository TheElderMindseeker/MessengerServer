terminat0r = '\0'


def send_by_socket(socket, string, address=None):
    if address is None:
        socket.sendall(bytes(string + terminat0r, 'ascii'))
    else:
        socket.sendto(bytes(string + terminat0r, 'ascii'), address)


def issue_error_message(socket, error, address=None):
    if address is None:
        send_by_socket(socket, 'Error;' + error)
    else:
        send_by_socket(socket, 'Error;' + error, address)


def recv_from_socket(socket, address=None):
    buffer = b''
    while str(buffer, 'ascii').find(terminat0r) == -1:
        if address is None:
            buffer += socket.recv(1024)
        else:
            bs, addr = socket.recvfrom(1024)
            if addr != address:
                raise ValueError
            buffer += bs

    s = str(buffer, 'ascii')
    s = s[:s.find(terminat0r)]

    return s


def recv_file_from_socket(socket, file_size, address=None):
    if address is None:
        buffer = socket.recv(file_size)
    else:
        bs, addr = socket.recvfrom(file_size)
        if addr != address:
            raise ValueError
        buffer = bs
    return buffer


def send_file_by_socket(socket, bin_array, address=None):
    if address is None:
        socket.sendall(bin_array)
    else:
        socket.sendto(bin_array, address)