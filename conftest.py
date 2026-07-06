"""Bootstrap de pytest: raíz del repo al sys.path + perfil determinista de hypothesis."""
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from hypothesis import settings

settings.register_profile("calibracion", deadline=None, max_examples=200, derandomize=True)
settings.load_profile("calibracion")
