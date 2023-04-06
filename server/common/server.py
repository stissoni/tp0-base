import socket
import logging
import signal
from common.utils import Bet, store_bets
from common.packet import Packet


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        logging.info("action: receive_sigterm_signal | result: exiting gracefully!")
        self.kill_now = True


def read_all(client_sock, data_len):
    # Helper function to recv n bytes or return None if EOF is hit
    data = b""
    while len(data) < data_len:
        packet = client_sock.recv(1)
        if not packet:
            return None
        data += packet
    return data


class Server:
    def __init__(self, port, listen_backlog):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("", port))
        self._server_socket.listen(listen_backlog)

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        killer = GracefulKiller()
        while not killer.kill_now:
            client_sock = self.__accept_new_connection()
            self.__handle_client_connection(client_sock)
        self._server_socket.close()
        logging.info("action: closing_sockets | result: sockets closed succesfully!")

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            bytes = read_all(client_sock, 4)
            serialization_len = int.from_bytes(bytes, byteorder="big")

            serialization_bytes = read_all(client_sock, serialization_len)

            request = Packet.deserialize(serialization_bytes)
            if request.type == "0":
                bet = Bet(
                    request.agency,
                    request.first_name,
                    request.last_name,
                    request.doc,
                    request.birthdate,
                    request.bet_num,
                )
                # Save the bet and log it
                store_bets([bet])
                logging.info(
                    f"action: apuesta_almacenada | result: success | dni: {request.doc} | numero: {request.bet_num}"
                )
                response = Packet("0", "OK")
                response = response.serialize()

                bytes_sent = 0
                while bytes_sent < len(response):
                    bytes_sent += client_sock.send(response[bytes_sent:])
            else:
                pass
        except OSError as e:
            logging.error(f"action: receive_message | result: fail | error: {e}")
        finally:
            client_sock.close()

    def __accept_new_connection(self):
        """
        Accept new connections

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        """

        # Connection arrived
        logging.info("action: accept_connections | result: in_progress")
        c, addr = self._server_socket.accept()
        logging.info(f"action: accept_connections | result: success | ip: {addr[0]}")
        return c
