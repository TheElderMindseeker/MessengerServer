import time as sleeper
import sqlite3
from application_layer import *


def request_handler(sock, addr, noise_level):
    """
    The main function which handles client requests
    :param sock: Socket connected with the client
    :param addr: Client address
    :param noise_level: Noise level for bit flipping (X channel)
    """
    flag_handshaked = False
    user_id = -1
    connection = sqlite3.connect('database.sqlite')
    cursor = connection.cursor()

    exit_cond = False
    while not exit_cond:
        sleeper.sleep(0.1)  # Used for saving CPU time when idling
        request = recv_from_socket(sock)

        # For list of requests and the actions specified for those, consider the protocol
        if request == 'Vkontakte is dead!':
            exit_cond, flag_handshaked = is_error(sock, addr, dispatch_handshake, flag_handshaked=flag_handshaked)
            exit_cond = False
        elif flag_handshaked:
            if request.startswith('Login;'):
                exit_cond, user_id = is_error(sock, addr, dispatch_login, cursor, connection, login=request[6:])
                exit_cond = False
            elif request.startswith('Get list of users'):
                exit_cond = is_error(sock, addr, dispatch_users, cursor)
                exit_cond = False
            elif request.startswith('Get messages;') and user_id != -1:
                time = request[13:]
                exit_cond = is_error(sock, addr, dispatch_messages, cursor, time=time, user_id=user_id)
                exit_cond = False
            elif request.startswith('Send;'):
                receiver_id, message_body = request[5:].split(';', maxsplit=1)
                receiver_id = int(receiver_id)
                exit_cond = is_error(sock, addr, dispatch_send, cursor, connection, user_id=user_id,
                                     receiver_id=receiver_id, message_body=message_body)
                exit_cond = False
            elif request.startswith('Send file;'):
                request = request[10:]
                receiver_id, message_body, file_name, file_size, compression, encoding = request.split(';', maxsplit=5)
                receiver_id = int(receiver_id)
                file_size = int(file_size)
                exit_cond = is_error(sock, addr, dispatch_send_file, cursor, connection, receiver_id=receiver_id,
                                     user_id=user_id, message_body=message_body, file_name=file_name,
                                     file_size=file_size, compression=compression, encoding=encoding)
            elif request.startswith('Recv file;'):
                file_id = int(request[10:])
                exit_cond = is_error(sock, addr, dispatch_recv_file, cursor, file_id=file_id, noise_level=noise_level)
                exit_cond = False
            elif request == 'Disconnect':
                send_by_socket(sock, 'Bye!', addr)
                exit_cond = True
            else:
                issue_error_message(sock, 'Unknown Request', addr)
                exit_cond = False
        else:
            exit_cond = False

    sock.close()
