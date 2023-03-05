FROM debian:bullseye-slim
ENV BTC_VERSION="23.0"
ADD https://bitcoincore.org/bin/bitcoin-core-${BTC_VERSION}/bitcoin-${BTC_VERSION}-x86_64-linux-gnu.tar.gz /home/btc.tar.gz
RUN tar -xzf /home/btc.tar.gz -C /home; \
    rm /home/btc.tar.gz; \
    install -m 0755 -o root -g root -t /usr/local/bin /home/bitcoin-${BTC_VERSION}/bin/*; \
    rm -r /home/bitcoin-${BTC_VERSION};
VOLUME /bitcoin
COPY ./configs/testnet.conf /bitcoin.conf
CMD ["bitcoind", "-conf=/bitcoin.conf"]
