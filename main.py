import json
import os

from VoltaLibPython import VoltaClient

def main():
    with VoltaClient() as client:
        print("Starting test")
        var = client.get.catalog.artist("YaboiMatoi")
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