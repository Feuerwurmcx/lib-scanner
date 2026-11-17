"""WEGWERF-VERSUCH: kleine Arbeitslast, die typische Zugriffe einer App erzeugt.

Jeder Abschnitt wird einzeln gestoppt, damit man sieht, welche Art von
Arbeit das Mitschneiden bremst (Datei-Zugriffe) und welche nicht (Rechnen).
"""
import subprocess
import time


def abschnitt(name, fn):
    start = time.perf_counter()
    try:
        fn()
        status = ""
    except Exception as exc:  # Versuch soll durchlaufen, auch wenn etwas fehlt
        status = f"  (Fehler: {exc!r})"
    print(f"ABSCHNITT {name:<24} {time.perf_counter() - start:8.3f} s{status}")


def importe():
    # Module mit nativen Bibliotheken dahinter (libssl, libsqlite3, libz, libffi ...)
    for mod in ("ssl", "sqlite3", "json", "decimal", "zlib", "hashlib",
                "ctypes", "xml.etree.ElementTree", "bz2", "lzma"):
        try:
            __import__(mod)
        except ImportError as exc:
            print(f"  import {mod} nicht moeglich: {exc}")


def sqlite():
    import sqlite3
    con = sqlite3.connect(":memory:")
    con.execute("create table t (a integer, b text)")
    con.executemany("insert into t values (?, ?)",
                    ((i, str(i)) for i in range(20000)))
    con.execute("select count(*), sum(a) from t").fetchone()


def tls():
    import ssl
    ssl.create_default_context()  # liest die CA-Zertifikate des Systems


def unterprozesse():
    # kurzlebige Prozesse: genau das, was ein Abfragen von /proc verpassen wuerde
    for _ in range(20):
        subprocess.run(["ls", "/"], capture_output=True, check=False)


def viele_dateien():
    # ungünstigster Fall fuer das Mitschneiden: sehr viele Datei-Oeffnungen
    for _ in range(5000):
        with open("/etc/os-release", "rb") as fh:
            fh.read()


def rechnen():
    sum(i * i for i in range(3_000_000))


if __name__ == "__main__":
    abschnitt("importe", importe)
    abschnitt("sqlite", sqlite)
    abschnitt("tls-zertifikate", tls)
    abschnitt("20 unterprozesse", unterprozesse)
    abschnitt("5000 datei-oeffnungen", viele_dateien)
    abschnitt("rechnen", rechnen)
