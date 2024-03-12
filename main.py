from client import Client
from server import Server
import asyncio

from multiprocessing import Process


def start_client():
    client = Client()
    client.start_pinging()


def start_server():
    server = Server()
    asyncio.run(server.start_server())


if __name__ == "__main__":
    p1 = Process(target=start_server, daemon=True)
    p2 = Process(target=start_client, daemon=True)
    p3 = Process(target=start_client, daemon=True)
    p1.start()
    p2.start()
    p3.start()
    p1.join()
    p2.join()
    p3.join()
    print("I'm done.")
