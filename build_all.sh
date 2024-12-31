#!/bin/bash

docker pull redis
docker pull ubuntu:jammy
for PROJ in ??_*; do
  ( cd ${PROJ}; ./build.sh )
done
