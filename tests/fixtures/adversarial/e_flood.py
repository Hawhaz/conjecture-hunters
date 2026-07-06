# Ataque: inunda stdout con 10^7 lineas; el sandbox trunca a 1 MB y rechaza.
print("\n".join("%d %d" % (i, i + 1) for i in range(10_000_000)))
