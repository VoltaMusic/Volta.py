import json
import os

from VoltaLibPython import VoltaClient

def main():
    with VoltaClient() as client:
        print("Starting test")
        var = client.get.catalog.playlist("bb7d0e57-bb01-4491-88b6-ce62ee3d75f0")
        print("Variable was fetched, saving to temp.json")

        with open("temp.json", "w") as f:
            json.dump(var, f, indent=4)

def pause():
    input("Press Enter to exit and clear...")

def clear():
    for filename in os.listdir("."):
        if filename.endswith(".json"):
            os.remove(filename)


if __name__ == "__main__":
    main()
    pause()
    clear()