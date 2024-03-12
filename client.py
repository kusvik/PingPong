import socket
import logging
import time
import random
from datetime import datetime
from config import HOST, PORT, LIFETIME_SECONDS


class Client:
    def __init__(self, host: str = HOST, port: int = PORT, lifetime_sec: int = LIFETIME_SECONDS, client_num: int = 1):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(1)
        self.lifetime_sec = lifetime_sec
        self.host = host
        self.port = port
        self.client_num = "_unknown"
        self.req_counter = 0
        self.last_answered = -1
        self.buffer = ["" for i in range(10)]
        self._set_logger()
        self.pending_logs = []

    def _set_logger(self):
        logger = logging.getLogger(f"{__name__}Client{self.client_num}")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f"client{self.client_num}.log")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger

    def connect(self) -> bool:
        retries = 3
        while retries:
            retries -= 1
            try:
                self.socket.connect((self.host, self.port))
                self.client_num = self.socket.recv(1024).decode('ascii')
                self._set_logger()
                self.logger.info(f"Connected to server {self.host}:{self.port}.")
                return True
            except (ConnectionRefusedError, TimeoutError) as e:
                time.sleep(5)
        logging.error(f"Connection to server {self.host}:{self.port} failed.")
        return False

    def disconnect(self):
        self.socket.close()
        self.logger.info("Connection closed.")
        res_time = datetime.now().time()
        while self.last_answered + 1 < self.req_counter:
            self.logger.info(f"{self.buffer[(self.last_answered + 1) % 10]}{res_time};(timeout);")
            # print("ignoring", self.last_answered, self.client_num)
            self.last_answered += 1

    def start_pinging(self):
        try:
            if not self.connect():
                return
            self.logger.info(f"Starting pinging for {self.lifetime_sec} seconds.")
            started = time.time()
            while time.time() < started + self.lifetime_sec:
                self.ping()
                time.sleep(random.randint(300, 3000) / 1000)
            self.logger.info("Time is up.")
        except (ConnectionAbortedError, ConnectionResetError) as e:
            self.logger.warning("Connection aborted by server.")
        finally:
            self.disconnect()

    def ping(self):
        letter = f"[{self.req_counter}] PING"
        req_datetime = datetime.now()
        req_log = f"{req_datetime.date()};{req_datetime.time()};{letter};"
        self.socket.sendall(letter.encode('ascii'))
        self.buffer[self.req_counter % 10] = req_log
        self.req_counter += 1
        try:
            data = self.socket.recv(1024).decode('ascii').split('\n')[:-1]
            res_time = datetime.now().time()

            if len(data) == 1 and data[0][-9:] == "keepalive":
                self.logger.info(f"{res_time};{data[0]};")
                data = self.socket.recv(1024).decode('ascii').split('\n')[:-1]
                res_time = datetime.now().time()

            for msg in data:
                if msg[-9:] == "keepalive":
                    self.logger.info(f"{res_time};{msg};")
                else:
                    req_num = int(msg[msg.find('/') + 1: msg.find(']')])
                    # print(f"answered to {req_num}", self.client_num)
                    while self.last_answered + 1 != req_num:
                        self.logger.info(f"{self.buffer[(self.last_answered + 1) % 10]}{res_time};(timeout);")
                        # print("ignoring", self.last_answered, self.client_num)
                        self.last_answered += 1
                    self.logger.info(f"{self.buffer[req_num % 10]}{res_time};{msg};")
                    self.last_answered += 1

        except TimeoutError:
            pass


if __name__ == "__main__":
    client = Client()
    client.start_pinging()
