from random import uniform
from transport_layer import *


def is_error(sock, addr, dispatcher, *args, **kwargs):
    """
    Wrapper function that checks the execution result of dispatcher
    :param sock: Socket connected with the client
    :param addr: Client address
    :param dispatcher: Dispatcher function for the request
    :param args: args which are passed directly to the dispatcher
    :param kwargs: keyword args that are passed directly to the dispatcher
    :return: Status of error
    """
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
    """
    Dispatches handshake when client first tries to establish connection
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: None for this function, only for compatibility
    :param kwargs: ['flag_handshaked'] - if the client already handshaked
    :return: Special dispatcher type, error status, new handshaked flag
    """
    dispatcher_type = 'handshake'
    if not kwargs['flag_handshaked']:
        # If the client has not yet handshaked, send him the response
        send_by_socket(sock, 'Long live Telegram!', addr)
    return dispatcher_type, kwargs['flag_handshaked'], True


def dispatch_login(sock, addr, *args, **kwargs):
    """
    Dispatches user login, fetches user data from database or creates new user, if needed
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: [0] - cursor to the database, [1] - connection to the database
    :param kwargs: ['login'] - login name
    :return: Special dispatcher type, error status, fetched or newly created user id
    """
    dispatcher_type = 'login'

    login = kwargs['login']
    if len(login) == 0:
        return dispatcher_type, True, 'Empty login name'

    cursor = args[0]
    connection = args[1]

    # Try to fetch user data from the database
    cursor.execute("SELECT count(*) FROM users WHERE login_name = ?;", (login,))
    count = cursor.fetchone()[0]
    if count == 0:
        # If user does not exist, create new user with such login
        cursor.execute("INSERT INTO users (login_name) VALUES (?);", (login,))
        user_id = cursor.lastrowid
        connection.commit()
    else:
        # If user exists, fetch his data from the database
        cursor.execute("SELECT user_id FROM users WHERE login_name = ?;", (login,))
        user_id = cursor.fetchone()[0]

    # Sending back user id according to database, see protocol
    send_by_socket(sock, 'Successful;' + str(user_id), addr)
    return dispatcher_type, False, user_id


def dispatch_users(sock, addr, *args, **kwargs):
    """
    Dispatches 'get list of users' request
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: [0] - cursor to the database
    :param kwargs: None for this function, only for compatibility
    :return: Special dispatcher type, error status
    """
    dispatcher_type = 'users'

    cursor = args[0]

    # Fetch all users from database
    cursor.execute('''SELECT * FROM users;''')
    response = 'Successful'
    for row in cursor.fetchall():
        # For each user, add her information to the response
        response += ';' + str(row[0]) + '|' + row[1]
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_messages(sock, addr, *args, **kwargs):
    """
    Dispatch 'get messages' request
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: [0] - cursor to the database
    :param kwargs: ['time'] - the bounding timestamp, ['user_id'] - user id of the requesting user
    :return: Special dispatcher type, error status
    """
    dispatcher_type = 'messages'

    cursor = args[0]
    time = kwargs['time']
    user_id = kwargs['user_id']

    if len(time) == 0:
        return dispatcher_type, True, 'Unspecified Timestamp'
    if user_id < 1:
        return dispatcher_type, True, 'Unlogged User'

    # current_timestamp is needed to keep the client informed of how fresh her data is
    cursor.execute('''SELECT datetime('now') AS current_timestamp''')
    current_timestamp = cursor.fetchone()[0]

    # Fetch all messages and (possibly) attached files from the database
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
        # For each message, append to response in specified format, see protocol
        response += ';' + str(row[0]) + '|' + str(row[1]) + '|' + row[2] + '|' + row[3] + '|' + str(row[4]) + '|' + str(row[5])
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_send(sock, addr, *args, **kwargs):
    """
    Dispatch 'send' request
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: [0] - cursor to the database, [1] - connection to the database
    :param kwargs: ['user_id'] - user id of the sending user, ['receiver_id'] - user id of message receiver,
    ['message_body'] - the contents of the message
    :return: Special dispatcher type, error status
    """
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

    # Add message to the database
    cursor.execute('''INSERT INTO messages
                                    (sender_id, receiver_id, timestamp, message_body)
                                      VALUES
                                    (?, ?, datetime('now'), ?)''', (user_id, receiver_id, message_body))
    connection.commit()

    cursor.execute('''SELECT timestamp FROM messages WHERE message_id = last_insert_rowid()''')
    timestamp = cursor.fetchone()[0]
    # Add message timestamp to the response
    response = 'Successful;' + timestamp
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_send_file(sock, addr, *args, **kwargs):
    """
    Dispatch 'send file' request
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: [0] - cursor to the database, [1] - connection to the database
    :param kwargs: ['user_id'] - user id of the sending user, ['receiver_id'] - user id of message receiver,
    ['message_body'] - the contents of the message, ['file_name'] - name of the sent file,
    ['file_size'] - the file size in bytes, ['compression'] - compression type of the file,
    ['encoding'] - encoding type of the file
    :return: Special dispatcher type, error status
    """
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
    # Insert file attributes into the database
    cursor.execute('''INSERT INTO files (file_name, file_size, compression_type, encoding_type) VALUES (?, ?, ?, ?);''',
                   (file_name, file_size, compression, encoding))
    file_id = cursor.lastrowid
    path = 'files/' + str(file_id) + '.file'
    output = open(path, 'bw')
    output.write(bytes(file))
    output.close()

    # Insert the message, to which the file is attached into the database
    cursor.execute('''INSERT INTO messages (sender_id, receiver_id, file_id, timestamp, message_body)
                      VALUES (?, ?, ?, datetime('now'), ?)''', (user_id, receiver_id, file_id, message_body))
    connection.commit()

    # Get newly inserted message timestamp
    cursor.execute('''SELECT timestamp FROM messages WHERE message_id = last_insert_rowid()''')
    timestamp = cursor.fetchone()[0]
    response = 'Successful;' + timestamp + ';' + str(file_id)
    send_by_socket(sock, response, addr)

    return dispatcher_type, False


def dispatch_recv_file(sock, addr, *args, **kwargs):
    """
    Dispatch 'recv file' request
    :param sock: Socket connected with the client
    :param addr: Client address
    :param args: [0] - cursor to the database
    :param kwargs: ['file_id'] - the id of the file to fetch,
    ['noise_level'] - level of noise when sending the file to client
    :return:
    """
    dispatcher_type = 'recv file'

    cursor = args[0]

    file_id = kwargs['file_id']
    noise_level = kwargs['noise_level']

    if file_id < 1:
        return dispatcher_type, True, 'Unknown file'

    # Fetch file attributes from the database
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
        # Send file, possibly with noise simulation to the client
        if noise_level > 1e-10:
            buffer = bytearray(file.read())
            for byte in range(len(buffer)):
                for i in range(8):
                    if uniform(0, 1) < noise_level:
                        buffer[byte]= buffer[byte] ^ (1 << i)
            send_file_by_socket(sock, bytes(buffer), addr)
        else:
            send_file_by_socket(sock, file.read(), addr)

    return dispatcher_type, False
