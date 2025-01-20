#!/bin/bash

REDIS_URL=redis://172.17.0.1:6379 PERIOD=max ./indicators2redis.py -t OS,AMTM
