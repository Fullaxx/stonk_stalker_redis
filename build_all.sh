#!/bin/bash

docker pull ubuntu:jammy
for PROJ in ??_*; do
  ( cd ${PROJ}; ./build.sh )
done

#( cd 01_*; ./build.sh )
#( cd 02_*; ./build.sh )
