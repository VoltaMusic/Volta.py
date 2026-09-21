import json
import os
import inspect

from VoltaLibPython import VoltaClient

def main():
    choice = input("Que voulez-vous tester (library/catalog) ? ").strip().lower()
    if choice not in ("library", "catalog"):
        print("Choix invalide.")
        return

    with VoltaClient() as client:
        results = {}
        root = getattr(client.get, choice)
        visited = set()

        def test_get_functions(obj, path):
            if id(obj) in visited:
                return
            visited.add(id(obj))

            for name in dir(obj):
                if name.startswith("_"):
                    continue
                try:
                    member = getattr(obj, name)
                except Exception:
                    continue
                member_path = f"{path}.{name}"

                if callable(member):
                    try:
                        signature = inspect.signature(member)
                    except (TypeError, ValueError):
                        continue
                    arguments = []
                    for parameter in signature.parameters.values():
                        if parameter.kind in (
                            parameter.POSITIONAL_ONLY,
                            parameter.POSITIONAL_OR_KEYWORD,
                        ) and parameter.default is parameter.empty:
                            arguments.append(
                                input(f"Valeur de {member_path}.{parameter.name}: ")
                            )
                    print(f"Test de {member_path}...")
                    try:
                        results[member_path] = member(*arguments)
                        print("  OK")
                    except Exception as error:
                        results[member_path] = {"error": str(error)}
                        print(f"  ERREUR: {error}")
                elif not isinstance(member, (str, bytes, int, float, bool)):
                    test_get_functions(member, member_path)

        test_get_functions(root, choice)
        with open("temp.json", "w") as f:
            json.dump(results, f, indent=4, default=str)
        print("Tests terminés. Résultats enregistrés dans temp.json")

def pause():
    input("Press Enter to exit and clear...")

def clear():
    for filename in os.listdir("."):
        if filename.endswith(".json"):
            os.remove(filename)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        raise
    pause()
    clear()