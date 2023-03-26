import socket
import logging
import signal
import json
from common.utils import Bet, store_bets, load_bets, has_won


class AgenciaNacional:
    def __init__(self):
        self.num_agencias = 5
        self.agencias_listas = 0
        self.sorteo_realizado = False

    def notificar_apuestas_cargadas(self, numero_agencia):
        self.agencias_listas += 1
        logging.info(
            f"action: apuestas_cargadas | agency : {numero_agencia} | agencias listas: {self.agencias_listas}"
        )

    def empezar_el_sorteo(self):
        if self.num_agencias == self.agencias_listas:
            logging.info("action: sorteo | result: success")
            self.sorteo_realizado = True
            return True
        return False

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

    def guardar_apuestas(self, bets: list[Bet]):
        logging.info(
            f"action: apuestas_almacenada | result: success | nuevas apuestas: {len(bets)}"
        )
        store_bets(bets)


class AgenciasAPI:
    def decode_bet(self, json_data):
        numero_agencia = json_data["agencia"]
        first_name = json_data["nombre"]
        last_name = json_data["apellido"]
        doc = json_data["doc"]
        birthdate = json_data["nacimiento"]
        numero = json_data["numero"]

        return Bet(numero_agencia, first_name, last_name, doc, birthdate, numero)

    def generate_response(self, request, agencia_nacional):
        # Check the request type and generate response
        if isinstance(request, dict):
            numero_agencia = request["agencia"]
            if request["type"] == "ready":
                agencia_nacional.notificar_apuestas_cargadas(numero_agencia)
                agencia_nacional.empezar_el_sorteo()
                json_response = {
                    "type": "ready",
                    "agencia": numero_agencia,
                    "message": "apuestas_cargadas",
                }

            if request["type"] == "consultar_ganadores":
                if not agencia_nacional.sorteo_realizado:
                    json_response = {
                        "type": "error",
                        "message": f"sorteo no realizado. Agencias listas: {agencia_nacional.agencias_listas}",
                    }
                else:
                    ganadores = agencia_nacional.consultar_ganadores(numero_agencia)
                    json_response = {
                        "type": "consultar_ganadores",
                        "agencia": numero_agencia,
                        "ganadores": f"{ganadores}",
                    }

        # Save the bet, log it and generate response
        if isinstance(request, list):
            bets = [self.decode_bet(json) for json in request]
            agencia_nacional.guardar_apuestas(bets)
            json_response = {
                "type": "batch_cargado",
                "message": f"cargado batch de {len(bets)} apuestas",
            }
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
        while not killer.kill_now:
            client_sock = self.__accept_new_connection()
            client_sock = SocketWrapper(client_sock)
            self.__handle_client_connection(client_sock, agencia)
        self._server_socket.close()
        logging.info("action: closing_sockets | result: sockets closed succesfully!")

    def __handle_client_connection(self, client_sock: SocketWrapper, agencia):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        api = AgenciasAPI()

        try:
            # Receive the data
            data = client_sock.receive_data()

            # Check request type and proceed
            response = api.generate_response(data, agencia)

            # Response client
            client_sock.send_data(response)

        except Exception as e:
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
