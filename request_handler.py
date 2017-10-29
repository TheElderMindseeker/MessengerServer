import sqlite3


def request_handler(sock, addr):
    flag_handshaked = False
    user_id = -1
    con = sqlite3.connect(":memory:")
    cur = con.cursor()
    while True:
        request = recv_from_socket(sock)
        #may do another While True for handshaked case (do not check if handshaked every time)
        if not flag_handshaked:
            if request == 'Vkontakte is dead!':
                flag_handshaked = True
                send_by_socket(sock, 'Long live Telegram!\0', addr)
            else:
                send_by_socket(sock, 'Wrong handshake!\0', addr)
        else:
            if request.split(':', maxsplit=1)[0] == 'Login':
                login = request.split(':', maxsplit=1)[1]
                cur.execute("SELECT count(*) FROM users WHERE login_name=\'?\';", login)
                count = cur.fetchone()
                if count[0] == 0:
                    cur.execute("INSERT INTO users VALUES (?);", (login))
                send_by_socket(sock, 'Successful\0', addr)
            elif request=='Get list of users':
                cur.execute("SELECT GROUP_CONCAT(login_name SEPARATOR\';\') FROM users;")
                send_by_socket(sock, 'Successful;'+cur.fetchone() + '\0', addr)
            elif request=='Disconnect':
                send_by_socket(sock, 'Bye\0', addr)
                break;
            else:
                send_by_socket(sock, request, addr)

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
