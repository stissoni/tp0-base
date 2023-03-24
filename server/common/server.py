import socket
import logging
import signal
import json
from common.utils import Bet, store_bets


class GracefulKiller:
    kill_now = False

    def __init__(self):
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, *args):
        logging.info("action: receive_sigterm_signal | result: exiting gracefully!")
        self.kill_now = True


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
            # Initialize an empty byte string to store the received data
            data = b""
            obj = None
            # Loop until the entire message has been received
            while True:
                # Receive up to 1024 bytes of data
                chunk = client_sock.recv(1024)

                # Check if the socket has been closed
                if not chunk:
                    # The socket has been closed, so break out of the loop
                    break

                # Append the received chunk to the data byte string
                data += chunk

                try:
                    obj = json.loads(data.decode("utf-8"))
                    # A complete JSON object has been received, so break out of the loop
                    break
                except json.JSONDecodeError:
                    # The received data is not a complete JSON object yet, so continue the loop
                    pass

            # Decode the received message

            agency = obj["agencia"]
            first_name = obj["nombre"]
            last_name = obj["apellido"]
            doc = obj["doc"]
            birthdate = obj["nacimiento"]
            bet_num = obj["numero"]

            bet = Bet(agency, first_name, last_name, doc, birthdate, bet_num)
            # Save the bet and log it
            store_bets([bet])
            logging.info(
                f"action: apuesta_almacenada | result: success | dni: {doc} | numero: {bet_num} "
            )

            msg = f"Apuesta {bet_num} recibida"
            msg_bytes = "{}\n".format(msg).encode("utf-8")
            bytes_sent = 0
            while bytes_sent < len(msg_bytes):
                bytes_sent += client_sock.send(msg_bytes[bytes_sent:])
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
