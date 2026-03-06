FROM nginx:alpine

# nginx config (must be inside build context)
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

# static site
COPY web/ /usr/share/nginx/html/
