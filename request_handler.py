import sqlite3

def request_handler(sock, addr):
    connection = sqlite3.connect('database.sqlite')
    cursor = connection.cursor()

    while True:
        request = recv_from_socket(sock)
        if request == 'Get list of users':
            cursor.execute('''SELECT login_name FROM users;''')
            user_list = ''
            for row in cursor.fetchall():
                user_list += ';' + row[0]
            response = 'Success' + user_list
            send_by_socket(sock, response, addr)
        else:
            issue_error_message(sock, 'Unknown Request', addr)
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