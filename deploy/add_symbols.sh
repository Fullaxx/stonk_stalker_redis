#!/bin/bash

if [ "$#" == "0" ]; then
  >&2 echo "$0: <SYMBOL> [SYMBOL] ..."
  exit 1
fi

while [ -n "$1" ]; do
  docker-compose exec -it yfinance /app/ticker2redis.py -s $1
  shift
done

docker-compose down
docker-compose up -d
