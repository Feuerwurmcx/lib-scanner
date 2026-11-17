#!/bin/bash
# WEGWERF-VERSUCH - geht nicht ins spaetere Werkzeug ein.
# Klaert drei Fragen:
#   1. Darf ein Prozess in diesem Namespace seine Kinder mit strace mitschneiden?
#   2. Wie stark bremst das?
#   3. Wie sehen die Rohdaten aus, und lassen sie sich RPM-Paketen zuordnen?
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${OUT:-/tmp/spike}
mkdir -p "$OUT"
export PYTHONDONTWRITEBYTECODE=1

echo "=== 1. Umgebung ==="
echo "user:         $(id)"
echo "kernel:       $(uname -r) $(uname -m)"
echo "ptrace_scope: $(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || echo 'nicht lesbar')"
grep -E '^(NoNewPrivs|Seccomp|CapEff|CapBnd):' /proc/self/status | sed 's/^/              /'
echo "python:       $(python3 -V 2>&1)"
if ! command -v strace >/dev/null 2>&1; then
  echo "strace:       FEHLT im Image"
  echo
  echo "ERGEBNIS mitschneiden: NICHT PRUEFBAR (strace fehlt im Image)"
  exit 2
fi
echo "strace:       $(strace -V 2>&1 | head -n1)"

echo
echo "=== 2. Lauf ohne Mitschneiden ==="
t0=$(date +%s%N)
python3 "$HERE/probe.py" 2>&1 | tee "$OUT/ohne.out"
t1=$(date +%s%N)

echo
echo "=== 3. Lauf mit Mitschneiden ==="
# Nur Datei-Oeffnen und Programmstart; '?' = Name ueberspringen, falls es ihn
# auf dieser Architektur / in dieser strace-Version nicht gibt.
CALLS='execve,?execveat,openat,?open,?openat2'
ok=""
for variante in "-f -z --seccomp-bpf" "-f -z" "-f"; do
  rm -f "$OUT/trace.log"
  echo "-- Versuch: strace $variante"
  t2=$(date +%s%N)
  # shellcheck disable=SC2086
  strace $variante -e trace="$CALLS" -s 256 -o "$OUT/trace.log" \
      python3 "$HERE/probe.py" >"$OUT/mit.out" 2>"$OUT/strace.err"
  rc=$?
  t3=$(date +%s%N)
  if [ "$rc" -eq 0 ] && grep -q 'execve(' "$OUT/trace.log" 2>/dev/null; then
    ok="$variante"
    cat "$OUT/mit.out"
    break
  fi
  echo "   fehlgeschlagen (Exit $rc):"
  head -n 5 "$OUT/strace.err" | sed 's/^/     /'
done

echo
if [ -z "$ok" ]; then
  echo "ERGEBNIS mitschneiden: BLOCKIERT - keine Variante hat funktioniert"
  echo "         (Fehlermeldungen stehen oben; diese bitte zurueckgeben)"
  exit 1
fi

echo "=== 4. Auswertung des Mitschnitts ==="
python3 "$HERE/summarize.py" "$OUT/trace.log"

echo
echo "=== 5. Ergebnis ==="
echo "ERGEBNIS mitschneiden: ERLAUBT mit 'strace $ok'"
python3 - "$t0" "$t1" "$t2" "$t3" <<'EOF'
import sys
t0, t1, t2, t3 = (int(x) for x in sys.argv[1:])
ohne, mit = (t1 - t0) / 1e9, (t3 - t2) / 1e9
print(f"ERGEBNIS laufzeit:     ohne {ohne:.2f} s, mit {mit:.2f} s, Faktor {mit / ohne:.2f}")
EOF
echo "ERGEBNIS mitschnitt:   $(wc -l < "$OUT/trace.log") Zeilen, $(du -k "$OUT/trace.log" | cut -f1) kB"
