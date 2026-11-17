"""WEGWERF-VERSUCH: wertet einen strace-Mitschnitt aus.

Zeigt, was spaeter die Grundlage der Urteile waere: gestartete Programme,
geladene Bibliotheken, geoeffnete Dateien - und zu welchem RPM-Paket sie gehoeren.
"""
import collections
import os
import re
import shutil
import subprocess
import sys

AUFRUF = re.compile(r'^(?:(\d+)\s+)?(execve|execveat|open|openat|openat2)\((.*)$')
FORTSETZUNG = re.compile(r'^(\d+)\s+<\.\.\. (\w+) resumed>.*=\s+(-?\d+)')
PFAD = re.compile(r'"((?:[^"\\]|\\.)*)"')
ERGEBNIS = re.compile(r'=\s+(-?\d+)\b[^=]*$')


def lese(datei):
    gestartet, geoeffnet = set(), set()
    offen = {}  # pid -> (syscall, pfad) fuer unterbrochene Aufrufe
    zeilen = 0
    with open(datei, errors="replace") as fh:
        for zeile in fh:
            zeilen += 1
            fort = FORTSETZUNG.match(zeile)
            if fort:
                pid, _, ret = fort.groups()
                if pid in offen and int(ret) >= 0:
                    call, pfad = offen[pid]
                    (gestartet if call.startswith("execve") else geoeffnet).add(pfad)
                offen.pop(pid, None)
                continue
            m = AUFRUF.match(zeile)
            if not m:
                continue
            pid, call, rest = m.groups()
            p = PFAD.search(rest)
            if not p:
                continue
            pfad = p.group(1)
            if "<unfinished" in rest:
                offen[pid] = (call, pfad)
                continue
            r = ERGEBNIS.search(rest)
            if r and int(r.group(1)) < 0:
                continue
            (gestartet if call.startswith("execve") else geoeffnet).add(pfad)
    return zeilen, gestartet, geoeffnet


def rpm_paket(pfad):
    if not shutil.which("rpm"):
        return None
    try:
        out = subprocess.run(
            ["rpm", "-qf", "--qf", "%{NAME} %{VERSION}-%{RELEASE}\n",
             os.path.realpath(pfad)],
            capture_output=True, text=True, timeout=20)
    except Exception:
        return None
    if out.returncode != 0:
        return "(kein RPM-Paket)"
    return out.stdout.strip().splitlines()[0]


def main(datei):
    zeilen, gestartet, geoeffnet = lese(datei)
    libs = sorted(p for p in geoeffnet if re.search(r'\.so(\.\d|$)', p))
    py = [p for p in geoeffnet if p.endswith((".py", ".pyc"))]
    sonst = sorted(geoeffnet - set(libs) - set(py))

    print(f"Zeilen im Mitschnitt:        {zeilen}")
    print(f"Gestartete Programme:        {len(gestartet)}")
    print(f"Geladene Bibliotheken (.so): {len(libs)}")
    print(f"Geoeffnete Python-Dateien:   {len(py)}")
    print(f"Sonstige geoeffnete Dateien: {len(sonst)}")

    pakete = collections.defaultdict(list)
    print("\n-- Gestartete Programme --")
    for p in sorted(gestartet):
        paket = rpm_paket(p)
        pakete[paket].append(p)
        print(f"  {p:<55} {paket or ''}")
    print("\n-- Geladene Bibliotheken --")
    for p in libs:
        paket = rpm_paket(p)
        pakete[paket].append(p)
        print(f"  {p:<55} {paket or ''}")
    print("\n-- Sonstige Dateien (erste 20) --")
    for p in sonst[:20]:
        print(f"  {p}")

    echte = sorted(k for k in pakete if k and not k.startswith("("))
    if echte:
        print(f"\n-- RPM-Pakete mit Beleg 'benutzt': {len(echte)} --")
        for k in echte:
            print(f"  {k:<45} ({len(pakete[k])} Datei(en))")
        try:
            alle = subprocess.run(["rpm", "-qa"], capture_output=True, text=True,
                                  timeout=60).stdout.split()
            print(f"\nInstallierte RPM-Pakete im Image: {len(alle)}"
                  f"  -> davon in diesem Lauf angefasst: {len(echte)}")
        except Exception:
            pass
    else:
        print("\n(Keine RPM-Zuordnung moeglich: 'rpm' fehlt im Image oder keine Treffer)")


if __name__ == "__main__":
    main(sys.argv[1])
