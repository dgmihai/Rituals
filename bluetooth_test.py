import asyncio
import array
from bleak import discover
from bleak import BleakClient
from bleak import BleakScanner

address = "C7:FB:14:97:F6:1C"
UUID_NORDIC_TX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
UUID_NORDIC_RX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
command = b"\x03\x10clearInterval()\n\x10setInterval(function() {LED.toggle()}, 500);\n\x10print('Hello World')\n"

def uart_data_received(sender, data):
    print("RX> {0}".format(data))

# You can scan for devices with:
#async def run():
#    devices = await discover()
#    for d in devices:
#        print(d)

#// Transmit Bluetooth Low Energy advertising packets
#NRF.setAdvertising({}, {
#    showName: false,
#    manufacturer: 0x0590,
#    manufacturerData: JSON.stringify({ name: "Bangle.js 2" })
#});

print("Connecting...")
async def connect(address, loop):
    async with BleakClient(address, loop=loop) as client:
        print("Connected")
        await client.start_notify(UUID_NORDIC_RX, uart_data_received)
        print("Writing command")
        c=command
        while len(c)>0:
          await client.write_gatt_char(UUID_NORDIC_TX, bytearray(c[0:20]), True)
          c = c[20:]
        print("Waiting for data")
        await asyncio.sleep(1.0, loop=loop) # wait for a response
        print("Done!")

async def scan():
    devices = await BleakScanner.discover()
    for d in devices:
        print(d)
        if d.name == "Bangle.js f61c":
            address = d.name

op = input('s for scan, c for connect, b for both\n')

loop = asyncio.get_event_loop()

if op == 's' or op == 'b':
    loop.run_until_complete(scan())
if op == 'c' or op == 'b':
    loop.run_until_complete(connect(address, loop))