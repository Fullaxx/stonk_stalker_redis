#!/bin/bash

echo "Stocks: "
docker-compose exec -it db redis-cli SMEMBERS DASHBOARD:SYMBOLS_SET:STOCKS
echo
echo "Crypto: "
docker-compose exec -it db redis-cli SMEMBERS DASHBOARD:SYMBOLS_SET:CRYPTO
