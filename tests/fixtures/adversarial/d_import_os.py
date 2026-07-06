# Ataque: import prohibido + intento de escribir un archivo.
# El AST check debe rechazarlo ANTES de ejecutar una sola linea.
import os

with open("hack.txt", "w") as f:
    f.write("pwned")
os.system("echo pwned")
print("0 1")
print("1 2")
print("2 0")
