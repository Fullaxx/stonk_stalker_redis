#!/bin/bash

docker pull ubuntu:jammy
docker build -t "fullaxx/ss_base_image" .
