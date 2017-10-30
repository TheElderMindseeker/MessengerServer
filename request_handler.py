import sqlite3


def request_handler(sock, addr):
    flag_handshaked = False
    user_id = -1
    connection = sqlite3.connect('database.sqlite')
    cursor = connection.cursor()

    while True:
        request = recv_from_socket(sock)

        if request == 'Vkontakte is dead!':
            if not flag_handshaked:
                flag_handshaked = True
                send_by_socket(sock, 'Long live Telegram!', addr)
            else:
                issue_error_message(sock, '', addr)
                break

        elif request[:6] == 'Login:' and user_id == -1:
            login = request.split(':', maxsplit=1)[1]
            cursor.execute("SELECT count(*) FROM users WHERE login_name=?;", (login,))
            count = cursor.fetchone()
            if count[0] == 0:
                cursor.execute("INSERT INTO users (login_name) VALUES (?);", (login,))
                connection.commit()

            cursor.execute("SELECT user_id FROM users WHERE login_name=?;", (login,))
            user_id = cursor.fetchone()[0]
            send_by_socket(sock, 'Successful', addr)

        elif request == 'Get list of users':
            cursor.execute('''SELECT login_name FROM users;''')
            response = 'Success'
            for row in cursor.fetchall():
                response += ';' + row[0]
            send_by_socket(sock, response, addr)

        elif request[:13] == 'Get messages;' and user_id != -1:
            time = request[13:]
            cursor.execute('''SELECT login_name, timestamp, COALESCE(message_body, 'File')
                            FROM(
                                SELECT 
                                 CASE WHEN receiver_id=:user_id THEN receiver_id ELSE sender_id END as login_id,
                                 message_body,
                                 timestamp
                                FROM messages 
                                WHERE (receiver_id=:user_id OR sender_id=:user_id) AND timestamp>=:time
                                )mes 
                                 INNER JOIN
                                users
                                ON mes.login_id=users.user_id''',
                           {"user_id": user_id, "time": time})
            response = 'Success'
            for row in cursor.fetchall():
                response += ';' + str(row[0]) + ":" + row[1] + ":" + row[2]
            send_by_socket(sock, response, addr)

        elif request[:5] == 'Send;':
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

        elif request[:10] == 'Send file;':
            request = request[10:]
            receiver_nick, file_name, size, compression, encoding = request.split(';', maxsplit=4)
            receiver_nick = receiver_nick.split(':', maxsplit=1)[1]
            file_name = file_name.split(':', maxsplit=1)[1]
            size = int(size.split(':', maxsplit=1)[1])
            compression = compression.split(':', maxsplit=1)[1]
            encoding = encoding.split(':', maxsplit=1)[1]

            send_by_socket(sock, 'Successful', addr)
            file = recv_file_from_socket(sock, size)
            cursor.execute('''INSERT INTO files (file_name, file_size, compression_type, encoding_type) VALUES (?, ?, ?, ?);''',
                           (file_name, size, compression, encoding))
            file_id = cursor.lastrowid
            path = 'files/' + file_name
            output = open(path, 'bw')
            output.write(file)
            output.close()

            cursor.execute('''SELECT user_id FROM users WHERE login_name=?''', (receiver_nick,))
            receiver_id = cursor.fetchone()
            if receiver_id is None:
                issue_error_message(sock, 'Unknown User', addr)
                continue
            receiver_id = receiver_id[0]

            cursor.execute('''INSERT INTO messages
                                        (sender_id, receiver_id, file_id, timestamp)
                                          VALUES
                                        (?, ?, ?, datetime(\'now\'))''', (user_id, receiver_id, file_id))
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
            buffer += bs

    s = str(buffer, 'ascii')
    s = s[:s.find('\n')]

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
