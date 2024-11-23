import asyncio
import sys

from core.client import Client


async def main(username: str, password: str, apply: bool):
    # Create a new client by supplying username and password
    ecactusecos = Client(username, password)

    # Authenticate the client by attempting to login
    # On success, the user id and authentication are set on the client
    await ecactusecos.authenticate()
    print("Authenticated")

    data = await ecactusecos.get_insight(offsetDay=-14)
    print("Insight %s" % data)

    strategy = await ecactusecos.create_dynamic_strategy(
        battery_capacity=40000,
        inverter_capacity=20000,
        charge=95,
        charge_price=0.08,
        discharge=25,
        discharge_price=0.25,
        profit=0.20,
        surcharge=0.025,
        surcharge_percentage=0,
    )
    # print("Strategy %s", strategy)

    if apply:
        await ecactusecos.set_strategy_info(strategy)
        print("Strategy applied")

    # # Manually logout the client.
    ecactusecos.invalidate_authentication()


if __name__ == "__main__":
    if len(sys.argv) - 1 == 2:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main(sys.argv[1], sys.argv[2], False))
    elif len(sys.argv) - 1 == 3:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(
            main(sys.argv[1], sys.argv[2], sys.argv[2] == 1))
    else:
        print("python example.py <username> <password> (<apply>)")
