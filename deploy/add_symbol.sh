#!/bin/bash

if [ -z "$1" ]; then
  >&2 echo "$0: <SYMBOL>"
  exit 1
fi

SYMBOL="$1"
docker-compose exec -it yfinance /app/ticker2redis.py -s ${SYMBOL}
