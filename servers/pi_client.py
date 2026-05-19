import asyncio
from websockets.asyncio.client import connect


async def recieve_from_ws():

    async with connect(f"ws://10.173.196.156:8765") as websocket:
        async for message in websocket:
            await websocket.send(message)
            print(message)


if __name__ == "__main__":
    asyncio.run(recieve_from_ws())