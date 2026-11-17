# WEGWERF-VERSUCH: Image nur fuer den Test, ob strace im Namespace erlaubt ist.
#
# BASE am besten auf euer eigenes SLES-15-SP7-Basis-Image (mit python3) setzen:
#   docker build --build-arg BASE=<eure-registry>/<basis-image>:<tag> -t <eure-registry>/lib-scanner-spike:1 spike/
ARG BASE=registry.suse.com/bci/python:3.11
FROM ${BASE}
USER root
RUN zypper --non-interactive install strace && zypper clean --all
