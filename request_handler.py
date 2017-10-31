import sqlite3
from application_layer import *


def request_handler(sock, addr):
    flag_handshaked = False
    user_id = -1
    connection = sqlite3.connect('database.sqlite')
    cursor = connection.cursor()

    exit_cond = False
    while not exit_cond:
        request = recv_from_socket(sock)

        if request == 'Vkontakte is dead!':
            exit_cond, flag_handshaked = is_error(sock, addr, dispatch_handshake, flag_handshaked=flag_handshaked)
        elif flag_handshaked:
            if request.startswith('Login;'):
                exit_cond, user_id = is_error(sock, addr, dispatch_login, cursor, connection, login=request[6:])
            elif request.startswith('Get list of users'):
                exit_cond = is_error(sock, addr, dispatch_users, cursor)
            elif request.startswith('Get messages;') and user_id != -1:
                time = request[13:]
                exit_cond = is_error(sock, addr, dispatch_messages, cursor, time=time, user_id=user_id)
            elif request.startswith('Send;'):
                receiver_id, message_body = request[5:].split(';', maxsplit=1)
                receiver_id = int(receiver_id)
                exit_cond = is_error(sock, addr, dispatch_send, cursor, connection, user_id=user_id,
                                     receiver_id=receiver_id, message_body=message_body)
            elif request.startswith('Send file;'):
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

            elif request.startswith('Recv file;'):
                file_id = int(request[10:])
                cursor.execute('''SELECT file_size, compression_type, encoding_type, file_name 
                                          FROM files WHERE file_id=?''', (file_id,))
                row = cursor.fetchone()
                answer = 'Successful;'
                answer += 'Size:' + str(row[0]) + ";"
                answer += 'Compression-Type:' + str(row[1]) + ";"
                answer += 'Coding-Type:' + str(row[2]) + ";"
                send_by_socket(sock, answer, addr)

                request = recv_from_socket(sock)
                if request == 'Accepting;':
                    path = 'files/' + str(row[3])
                    file = open(path, "rb")
                    send_file_by_socket(sock, file.read(), addr)

            elif request == 'Disconnect':
                send_by_socket(sock, 'Bye!', addr)
                exit_cond = True
            else:
                issue_error_message(sock, 'Unknown Request', addr)
                exit_cond = True
        else:
            exit_cond = True

    sock.close()
