# Description
The service is a solution for adding crypto payments to your application.

It has a rest API that allows you to get a new payment address for each payment. You should transfer this address to your client.
After the client has made a payment, the service will notify your application using a callback in the form of http request.
Callbacks will be repeated with each change in the number of payment transaction confirmations.
To stop receiving callbacks, send stop flag in the response.

For your convenience, you can use the us dollar to bitcoin converter when requesting a new payment address.
Also, the service will automatically transfer incoming funds to your own crypto wallet, which address is specified in settings.

For more details refer to openapi at /docs.

The service requires a full bitcoin node to operate. If you already have your own node or cloud node, you can use it by specifying the appropriate settings in .env file and remove the bitcoin service from the compose file.
# Requirements
- docker engine
- 500 Gb free disk space for mainnet and 50 Gb for testnet, if you are not using a cloud node
# Running dev environment
Build app image
```
docker build -t cps:1.0.0 .
```
Build bitcoin node image, if you want to use your own node instead of the cloud
```
cd deploy/bitcoin
docker build --tag bitcoin:23.0 -f testnet.dockerfile .
```
Create volumes
```
docker volume create cps_postgres
docker volume create cps_bitcoin
```
Before stating the service for the first time it's recommended to synchronize your local blockchain, because initial block download takes much time.
To do this run the following and wait until the progress field in the logs takes a value close to one
```
docker container run --rm -it -v bitcoin:/bitcoin bitcoin:23.0
```
Fill in the .env file according to the example(deploy/env_example)

Start the service
```
docker compose --file compose.yaml up -d
```
Initialize a database
```
docker compose --file compose.yaml exec api alembic upgrade head
```
# Running prod environment
Production environment service deployment depends on your infrastructure, so it's up to you.
A few things to do is to set environment variable TESTNET to false and to build bitcoin node from mainnet dockerfile.
