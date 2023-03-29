import socket
import logging
import signal
import json
from common.utils import Bet, store_bets, load_bets, has_won
from multiprocessing import Process, Lock, Barrier


class AgenciaNacional:
    def consultar_ganadores(self, numero_agencia):
        logging.info(f"action: consultar_ganadores | agency : {numero_agencia}")
        bets = load_bets()
        ganadores = 0
        for bet in bets:
            if has_won(bet):
                logging.info(
                    f"Encontrado el ganador: {bet.agency},{bet.first_name},{bet.last_name},{bet.number}"
                )
                if int(numero_agencia) == int(bet.agency):
                    logging.info(f"Sumando un ganador a la agencia {numero_agencia}")
                    ganadores = ganadores + 1
        return ganadores

    def guardar_apuestas(self, bets: list[Bet], lock):
        lock.acquire()
        store_bets(bets)
        lock.release()
        logging.info(
            f"action: apuestas_almacenada | result: success | nuevas apuestas: {len(bets)}"
        )


class AgenciasAPI:
    def decode_bet(self, json_data):
        numero_agencia = json_data["agencia"]
        first_name = json_data["nombre"]
        last_name = json_data["apellido"]
        doc = json_data["doc"]
        birthdate = json_data["nacimiento"]
        numero = json_data["numero"]

        return Bet(numero_agencia, first_name, last_name, doc, birthdate, numero)

    def generate_response(self, request, agencia_nacional, lock, barrier):
        # Check the request type and generate response
        if isinstance(request, dict):
            numero_agencia = request["agencia"]
            if request["type"] == "ready":
                logging.info("action: request de 'ready' recibida | status: processing")
                json_response = {
                    "type": "ready",
                    "agencia": numero_agencia,
                    "message": "apuestas_cargadas",
                }
                logging.info(
                    f"action: request de 'ready' recibida | status: complete | response: {json_response}"
                )
                return json_response

            if request["type"] == "consultar_ganadores":
                logging.info(
                    "action: request de 'consultar ganadores' recibida | status: waiting"
                )
                barrier.wait()
                ganadores = agencia_nacional.consultar_ganadores(numero_agencia)
                json_response = {
                    "type": "consultar_ganadores",
                    "agencia": numero_agencia,
                    "ganadores": f"{ganadores}",
                }
                logging.info(
                    f"action: request de 'consultar ganadores' recibida | status: complete | response: {json_response}"
                )
            return json_response

        # Save the bet, log it and generate response
        if isinstance(request, list):
            logging.info(
                "action: request de 'store batch' recibida | status: processing"
            )
            bets = [self.decode_bet(json) for json in request]
            try:
                agencia_nacional.guardar_apuestas(bets, lock)
                json_response = {
                    "type": "batch_cargado",
                    "message": f"cargado batch de {len(bets)} apuestas",
                }
            except:
                logging.error("error saving bets")
                json_response = {
                    "type": "batch_cargado",
                    "message": f"ERORR: no fue posible guardar batch de {len(bets)} apuestas",
                }
            logging.info(
                f"action: request de 'store batch' recibida | status: complete | response: {json_response}"
            )
            return json_response


class SocketWrapper:
    def __init__(self, socket):
        self.socket = socket

    def send_data(self, json_data):
        json_string = json.dumps(json_data)
        msg_bytes = "{}\n".format(json_string).encode("utf-8")

        # Solve short write problem
        bytes_sent = 0
        while bytes_sent < len(msg_bytes):
            bytes_sent += self.socket.send(msg_bytes[bytes_sent:])

        # logging.info(f"Paquete enviado: {json_data}")

    def receive_data(self):
        # Initialize an empty byte string to store the received data
        data = b""
        # Loop until the entire message has been received
        while True:
            # Receive up to 1024 bytes of data
            chunk = self.socket.recv(1024)

            # Check if the socket has been closed
            if not chunk:
                # The socket has been closed, so break out of the loop
                break

            # Append the received chunk to the data byte string
            data += chunk

            try:
                json_data = json.loads(data.decode("utf-8"))
                # A complete JSON object has been received, so break out of the loop
                data = json_data

                # logging.info(f"Paquete recibido: {data}")
                return data
            except (json.JSONDecodeError, UnicodeDecodeError):
                # The received data is not a complete JSON object yet, so continue the loop
                pass

    def close(self):
        self.socket.close()


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
        agencia = AgenciaNacional()
        killer = GracefulKiller()
        lock = Lock()
        barrier = Barrier(5)
        while not killer.kill_now:
            client_sock = self.__accept_new_connection()
            client_sock = SocketWrapper(client_sock)
            p = Process(
                target=self.__handle_client_connection,
                args=(client_sock, agencia, lock, barrier),
            )
            p.start()
        self._server_socket.close()
        logging.info("action: closing_sockets | result: sockets closed succesfully!")

    def __handle_client_connection(
        self, client_sock: SocketWrapper, agencia, lock, barrier
    ):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        api = AgenciasAPI()

        while True:
            # Receive the data
            logging.info("action: wating for data from clientes...")
            data = client_sock.receive_data()

            # Check request type and proceed
            response = api.generate_response(data, agencia, lock, barrier)

            # Response client
            client_sock.send_data(response)

            if response["type"] == "consultar_ganadores":
                # El protocolo termino ok. Salimos del loop.
                break

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
