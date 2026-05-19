import asyncio
from websockets.asyncio.server import serve

packet = "No"
def get_packet():
    return packet

def set_packet(new_packet):
    global packet
    packet = new_packet

async def send_to_pi(websocket):
    await websocket.send(get_packet())
    message = await websocket.recv()



async def main():
    async with serve(send_to_pi, "10.173.196.156", 8765) as server:
        await server.serve_forever()


def run_main(packet):
    set_packet(packet)
    asyncio.run(main())

run_main(packet)