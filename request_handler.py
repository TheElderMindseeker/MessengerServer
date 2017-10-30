import sqlite3


def request_handler(sock, addr):
    flag_handshaked = False
    user_id = -1
    connection = sqlite3.connect('database.sqlite')
    cursor = connection.cursor()

    while True:
        request = recv_from_socket(sock)
        # may do another While True for handshaked case (do not check if handshaked every time)
        if request == 'test':
            flag_handshaked = True
            cursor.execute("SELECT user_id FROM users WHERE login_name='Daniil';")
            user_id = cursor.fetchone()
            send_by_socket(sock, 'Successful; Hello Daniil', addr)
        elif request == 'Vkontakte is dead!':
            if not flag_handshaked:
                flag_handshaked = True
                send_by_socket(sock, 'Long live Telegram!', addr)
            else:
                issue_error_message(sock, '', addr)
                break
        elif request[:5] == 'Login' and user_id == -1:
            login = request.split(':', maxsplit=1)[1]
            cursor.execute("SELECT count(*) FROM users WHERE login_name=?;", (login,))
            count = cursor.fetchone()
            if count[0] == 0:
                cursor.execute("INSERT INTO users (login_name) VALUES (?);", (login,))
                connection.commit()
            cursor.execute("SELECT user_id FROM users WHERE login_name=?;", (login,))
            user_id = cursor.fetchone()
            send_by_socket(sock, 'Successful', addr)
        elif request == 'Get list of users':
            cursor.execute('''SELECT login_name FROM users;''')
            response = 'Success'
            for row in cursor.fetchall():
                response += ';' + row[0]
            send_by_socket(sock, response, addr)
        elif request[:12] == 'Get messages' and user_id != -1:
            time = request[13:]
            cursor.execute('''SELECT 
                             IF(receiver_id=:user_id, receiver_id, sender_id) as login,
                             message_body,
                             timestamp
                            FROM messages 
                            WHERE (receiver_id=:user_id OR sender_id=:user_id) AND timestamp>:time''',
                            {"user_id": user_id, "time": time})
            response = 'Success'
            for row in cursor.fetchall():
                response += row[0] + ":" + row[1]  + ":"  + row[2]
            send_by_socket(sock, response, addr)
        elif request[:4] == 'Send':
            receiver_nick, message_body = request[5:].split(';', maxsplit=1)
            cursor.execute('''SELECT user_id FROM users WHERE login_name=?''', (receiver_nick,))
            receiver_id = cursor.fetchone()
            if receiver_id is None:
                issue_error_message(sock, 'Unknown User', addr)
                continue
            receiver_id = receiver_id[0]
            cursor.execute('''INSERT INTO messages
                            (sender_id, receiver_id, timestamp, message_body)
                              VALUES
                            (?, ?, datetime(\'now\'), ?)''', (user_id, receiver_id, message_body))
            connection.commit()
            cursor.execute('''SELECT timestamp FROM messages WHERE message_id=last_insert_rowid()''')
            timestamp = cursor.fetchone()[0]
            answer = 'Successful;' + timestamp
            send_by_socket(sock, answer, addr)
        elif request == 'Disconnect':
            send_by_socket(sock, 'Bye!', addr)
            break
        else:
            issue_error_message(sock, 'Unknown Request', addr)
            break

    sock.close()


def send_by_socket(socket, string, address=None):
    if address is None:
        socket.sendall(bytes(string + '\n', 'ascii'))
    else:
        socket.sendto(bytes(string + '\n', 'ascii'), address)


def issue_error_message(socket, error, address=None):
    if address is None:
        socket.sendall(bytes('Error;' + error + '\n', 'ascii'))
    else:
        socket.sendto(bytes('Error;' + error + '\n', 'ascii'), address)


def recv_from_socket(socket, address=None):
    buffer = b''
    while str(buffer, 'ascii').find('\n') == -1:
        if address is None:
            buffer += socket.recv(1024)
        else:
            bs, addr = socket.recvfrom(1024)
            if addr != address:
                raise ValueError

    s = str(buffer, 'ascii')
    s = s[:s.find('\n')]

    return s
