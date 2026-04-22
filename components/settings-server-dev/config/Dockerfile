FROM hashicorp/vault:1.21

RUN apk add --no-cache curl bash jq

COPY config.hcl /vault/config/config.hcl
COPY entrypoint.sh /vault_entrypoint.sh
RUN chmod +x /vault_entrypoint.sh

ENTRYPOINT ["/vault_entrypoint.sh"]