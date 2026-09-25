#!/usr/bin/env bash
# Lance le lint (ruff), le typage (mypy) et les tests sur chaque version de Python supportée, comme le CI.
#
# Usage :
#   scripts/test_matrix.sh              # 3.10, 3.11, 3.12 et 3.13
#   scripts/test_matrix.sh 3.12 3.13    # seulement ces versions
#
# Nécessite uv (https://docs.astral.sh/uv/) : il télécharge les versions de
# Python manquantes et crée un environnement temporaire par version, sans
# toucher au .venv du projet.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

VERSIONS=("$@")
if [ ${#VERSIONS[@]} -eq 0 ]; then
	VERSIONS=(3.10 3.11 3.12 3.13)
fi

if command -v uv >/dev/null 2>&1; then
	UV=uv
elif [ -x .venv/Scripts/uv.exe ]; then
	UV=.venv/Scripts/uv.exe
elif [ -x .venv/bin/uv ]; then
	UV=.venv/bin/uv
else
	echo "uv introuvable. Installe-le avec : pip install uv" >&2
	exit 1
fi

failed=()
for version in "${VERSIONS[@]}"; do
	echo "=== Python ${version}"
	run=("$UV" run -q --no-project --python "$version" --with-editable .[dev] --)
	if "${run[@]}" python -m ruff check . \
		&& "${run[@]}" python -m mypy \
		&& "${run[@]}" python -m pytest -q -p no:cacheprovider; then
		echo "--> Python ${version} : OK"
	else
		echo "--> Python ${version} : ÉCHEC"
		failed+=("$version")
	fi
	echo
done

if [ ${#failed[@]} -eq 0 ]; then
	echo "Toutes les versions passent : ${VERSIONS[*]}"
	exit 0
fi
echo "Échec sur : ${failed[*]}" >&2
exit 1
