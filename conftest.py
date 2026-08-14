import sys
from pathlib import Path

# Torna o pacote (em src/) importável nos testes sem instalar.
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
