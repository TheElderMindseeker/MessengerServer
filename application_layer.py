from transport_layer import *


def is_error(sock, addr, dispatcher, *args, **kwargs):
    dispatcher_type, error, *result = dispatcher(sock, addr, *args, **kwargs)
    if dispatcher_type == 'handshake':
        if error:
            issue_error_message(sock, 'Already Handshaked', addr)
        return error, result[0]
    elif dispatcher_type == 'login':
        if error:
            issue_error_message(sock, result[0], addr)
        return error, result[0]
    elif dispatcher_type == 'users':
        if error:
            issue_error_message(sock, 'Unknown Error', addr)
        return error
    elif dispatcher_type == 'messages':
        if error:
            issue_error_message(sock, result[0], addr)
        return error
    elif dispatcher_type == 'send':
        if error:
            issue_error_message(sock, result[0], addr)
        return error
    elif dispatcher_type == 'send file':
        if error:
            issue_error_message(sock, result[0], addr)
        return error
    elif dispatcher_type == 'recv file':
        if error:
            issue_error_message(sock, result[0], addr)
        return error
    else:
        return True


def dispatch_handshake(sock, addr, *args, **kwargs):
    dispatcher_type = 'handshake'
    if not kwargs['flag_handshaked']:
        send_by_socket(sock, 'Long live Telegram!', addr)
    return dispatcher_type, kwargs['flag_handshaked'], True


def dispatch_login(sock, addr, *args, **kwargs):
    dispatcher_type = 'login'

    login = kwargs['login']
    if len(login) == 0:
        return dispatcher_type, True, 'Empty login name'

    cursor = args[0]
    connection = args[1]

    cursor.execute("SELECT count(*) FROM users WHERE login_name = ?;", (login,))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO users (login_name) VALUES (?);", (login,))
        user_id = cursor.lastrowid
        connection.commit()
    else:
        cursor.execute("SELECT user_id FROM users WHERE login_name = ?;", (login,))
        user_id = cursor.fetchone()[0]

    send_by_socket(sock, 'Successful;' + str(user_id), addr)
    return dispatcher_type, False, user_id


def dispatch_users(sock, addr, *args, **kwargs):
    dispatcher_type = 'users'

    cursor = args[0]

    cursor.execute('''SELECT * FROM users;''')
    response = 'Successful'
    for row in cursor.fetchall():
        response += ';' + str(row[0]) + '|' + row[1]
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_messages(sock, addr, *args, **kwargs):
    dispatcher_type = 'messages'

    cursor = args[0]
    time = kwargs['time']
    user_id = kwargs['user_id']

    if len(time) == 0:
        return dispatcher_type, True, 'Unspecified Timestamp'
    if user_id < 1:
        return dispatcher_type, True, 'Unlogged User'

    cursor.execute('''SELECT datetime('now') AS current_timestamp''')
    current_timestamp = cursor.fetchone()[0]

    cursor.execute('''SELECT sender_id, receiver_id, timestamp, 
                        COALESCE(message_body, ''), COALESCE(file_id, ''), COALESCE(file_name, '')
                        FROM
                            (SELECT sender_id, receiver_id, timestamp, message_body, file_id as mess_file_id
                            FROM messages
                            WHERE (receiver_id = :user_id OR sender_id = :user_id) AND timestamp >= :time) mess
                            LEFT JOIN
                            (SELECT file_name, file_id FROM files) fil
                            ON mess_file_id=file_id''',
                   {"user_id": user_id, "time": time})

    response = 'Successful;' + current_timestamp
    for row in cursor.fetchall():
        response += ';' + str(row[0]) + '|' + str(row[1]) + '|' + row[2] + '|' + row[3] + '|' + str(row[4]) + '|' + str(row[5])
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_send(sock, addr, *args, **kwargs):
    dispatcher_type = 'send'

    cursor = args[0]
    connection = args[1]

    user_id = kwargs['user_id']
    receiver_id = kwargs['receiver_id']
    message_body = kwargs['message_body']

    if user_id < 1:
        return dispatcher_type, True, 'Unlogged User'
    if receiver_id < 1:
        return dispatcher_type, True, 'Unknown Receiver'

    cursor.execute('''INSERT INTO messages
                                    (sender_id, receiver_id, timestamp, message_body)
                                      VALUES
                                    (?, ?, datetime('now'), ?)''', (user_id, receiver_id, message_body))
    connection.commit()

    cursor.execute('''SELECT timestamp FROM messages WHERE message_id = last_insert_rowid()''')
    timestamp = cursor.fetchone()[0]
    response = 'Successful;' + timestamp
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_send_file(sock, addr, *args, **kwargs):
    dispatcher_type = 'send file'

    cursor = args[0]
    connection = args[1]

    user_id = kwargs['user_id']
    receiver_id = kwargs['receiver_id']
    message_body = kwargs['message_body']
    file_name = kwargs['file_name']
    file_size = kwargs['file_size']
    compression = kwargs['compression']
    encoding = kwargs['encoding']

    if user_id < 1:
        return dispatcher_type, True, 'Unlogged User'
    if receiver_id < 1:
        return dispatcher_type, True, 'Unknown Receiver'

    send_by_socket(sock, 'Successful', addr)
    file = recv_file_from_socket(sock, file_size)
    cursor.execute('''INSERT INTO files (file_name, file_size, compression_type, encoding_type) VALUES (?, ?, ?, ?);''',
                   (file_name, file_size, compression, encoding))
    file_id = cursor.lastrowid
    path = 'files/' + str(file_id) + '.file'
    output = open(path, 'bw')
    output.write(file)
    output.close()

    cursor.execute('''INSERT INTO messages (sender_id, receiver_id, file_id, timestamp, message_body)
                      VALUES (?, ?, ?, datetime('now'), ?)''', (user_id, receiver_id, file_id, message_body))
    connection.commit()

    cursor.execute('''SELECT timestamp FROM messages WHERE message_id = last_insert_rowid()''')
    timestamp = cursor.fetchone()[0]
    response = 'Successful;' + timestamp + ';' + str(file_id)
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_recv_file(sock, addr, *args, **kwargs):
    dispatcher_type = 'recv file'

    cursor = args[0]

    file_id = kwargs['file_id']

    if file_id < 1:
        return dispatcher_type, True, 'Unknown file'

    cursor.execute('''SELECT file_name, file_size, compression_type, encoding_type, file_name 
                                              FROM files WHERE file_id = ?''', (file_id,))
    row = cursor.fetchone()
    response = 'Successful;'
    response += str(row[0]) + ';'
    response += str(row[1]) + ';'
    response += str(row[2]) + ';'
    response += str(row[3])
    send_by_socket(sock, response, addr)

    request = recv_from_socket(sock)
    if request == 'Accepting':
        path = 'files/' + str(file_id) + '.file'
        file = open(path, "rb")
        send_file_by_socket(sock, file.read(), addr)

    return dispatcher_type, False
