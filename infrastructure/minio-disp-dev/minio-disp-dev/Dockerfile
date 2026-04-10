FROM minio/mc:RELEASE.2025-08-13T08-35-41Z AS mc

FROM alpine:3.20
RUN apk add --no-cache jq

COPY --from=mc /usr/bin/mc /usr/bin/mc
COPY config/ /config/

RUN mv /config/buckets.json /buckets.json \
 && mv /config/setup.sh /setup.sh \
 && chmod +x /setup.sh