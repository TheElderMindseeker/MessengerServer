import sqlite3

def request_handler(sock, addr):
    flag_handshaked = False
    user_id = -1
    connection = sqlite3.connect('database.sqlite')
    cursor = connection.cursor()

    while True:
        request = recv_from_socket(sock)
        # may do another While True for handshaked case (do not check if handshaked every time)
        if request == 'Vkontakte is dead!':
            if not flag_handshaked:
                flag_handshaked = True
                send_by_socket(sock, 'Long live Telegram!', addr)
            else:
                issue_error_message(sock, '', addr)
                break
        elif request[:5] == 'Login':
            if request.split(':', maxsplit=1)[0] == 'Login':
                login = request.split(':', maxsplit=1)[1]
                cursor.execute("SELECT count(*) FROM users WHERE login_name=\'?\';", login)
                count = cursor.fetchone()
                if count[0] == 0:
                    cursor.execute("INSERT INTO users (login_name) VALUES (?);", (login))
                send_by_socket(sock, 'Successful', addr)
        elif request == 'Get list of users':
            cursor.execute('''SELECT login_name FROM users;''')
            response = 'Success'
            for row in cursor.fetchall():
                response += ';' + row[0]
            send_by_socket(sock, response, addr)
        elif request == 'Disconnect':
            send_by_socket(sock, 'Bye!', addr)
            break
        else:
            break

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
