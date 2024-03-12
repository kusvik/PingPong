import asyncio
import socket
import logging
import random
import types
import selectors
import time
from datetime import datetime
from config import HOST, PORT, LIFETIME_SECONDS


class Server:
    def __init__(self, host: str = HOST, port: int = PORT, lifetime_sec: int = LIFETIME_SECONDS):
        self.connections = {}
        self.ans_num = 0
        self.con_num = 0
        self.lifetime_sec = lifetime_sec
        self.timer = None
        self._set_logger()
        self.address = host, port
        self.sel = selectors.DefaultSelector()

        # setting up the register
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((host, port))
        self.socket.setblocking(False)
        self.sel = selectors.DefaultSelector()
        self.sel.register(self.socket, selectors.EVENT_READ, data=None)

    def _set_logger(self):
        logger = logging.getLogger(f"{__name__}Server")
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(f"server.log")
        formatter = logging.Formatter("%(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        self.logger = logger

    def _accept_wrapper(self, sock):
        conn, addr = sock.accept()  # Should be ready to read
        self.con_num += 1
        self.connections[conn] = self.con_num
        self.logger.info(f"Accepted connection from {addr[0]}:{addr[1]}")
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        self.sel.register(conn, events, data=data)
        conn.sendall(str(self.con_num).encode('ascii'))

    async def _service_connection(self, key, mask):
        conn = key.fileobj
        data = key.data
        req_log = ""
        try:
            if mask & selectors.EVENT_READ:
                recv_data = conn.recv(1024).decode('ascii')  # Should be ready to read
                req_datetime = datetime.now()
                if recv_data:
                    req_log = f"{req_datetime.date()};{req_datetime.time()};{recv_data};"
                    if not random.randint(0, 9):
                        self.logger.info(f"{req_log}(ignored);")
                        return
                    await asyncio.sleep(random.randint(100, 1000) / 1000)
                    data.outb += f"[{self.ans_num}/{recv_data[1:-6]}] PONG ({self.connections[conn]})\n".encode('ascii')
                else:
                    self.close_conn(conn)
            if mask & selectors.EVENT_WRITE and data.outb:
                sent = conn.send(data.outb)  # Should be ready to write
                res_time = datetime.now().time()
                self.logger.info(f"{req_log}{res_time};{data.outb.decode()[:-1]};")
                data.outb = data.outb[sent:]
                self.ans_num += 1
        except ConnectionResetError:
            self.logger.warning(f"Connection aborted by client {conn.getpeername()[0]}:{conn.getpeername()[1]}.")
            self.close_conn(conn)

    def close_conn(self, conn):
        self.logger.info(f"Closing connection with {conn.getpeername()[0]}:{conn.getpeername()[1]}.")
        self.sel.unregister(conn)
        del self.connections[conn]
        conn.close()

    async def start_server(self):
        self.socket.listen()
        self.timer = time.time() + self.lifetime_sec
        task1 = asyncio.create_task(self.listen())
        task2 = asyncio.create_task(self.keep_alive())
        await task1
        await task2
        self.logger.info("Time is up.")
        self.shut_down()

    async def listen(self):
        self.logger.info("Starting listening.")
        while self.timer is None or self.timer > time.time():
            events = self.sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    self._accept_wrapper(key.fileobj)
                else:
                    await self._service_connection(key, mask)

    async def keep_alive(self):
        while self.timer is None or self.timer > time.time():
            for conn in self.connections:
                conn.sendall(f"[{self.ans_num}] keepalive\n".encode('ascii'))
            self.ans_num += 1
            await asyncio.sleep(5)

    def shut_down(self):
        self.logger.info("Shutting down the server.")
        for conn in self.connections:
            self.sel.unregister(conn)
            conn.close()
        self.connections = {}
        self.socket.close()

    def close_register(self):
        self.sel.close()


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start_server())
