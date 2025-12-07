FROM alpine:latest

RUN apk add --no-cache util-linux coreutils

WORKDIR /app

COPY worker.sh .

RUN chmod +x worker.sh

CMD ["./worker.sh"]