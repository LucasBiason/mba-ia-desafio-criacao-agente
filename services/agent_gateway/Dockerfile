FROM nginx:alpine@sha256:4a73073bd557c65b759505da037898b61f1be6cbcc3c2c3aeac22d2a470c1752
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --chmod=755 entrypoint.sh /usr/local/bin/aurora-gateway-entrypoint
ENTRYPOINT ["/usr/local/bin/aurora-gateway-entrypoint"]
CMD ["nginx", "-g", "daemon off;"]
EXPOSE 80
