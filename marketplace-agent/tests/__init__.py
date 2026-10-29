"""Suite de testes do mktagent.

Coloca ``src/`` no sys.path para rodar sem instalar o pacote:
    python3 -m unittest discover -s tests -t .
"""

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
