FROM nginx:1.21-alpine
 
# Remove default config
RUN rm /etc/nginx/conf.d/default.conf
 
# Create SSL directory
RUN mkdir -p /etc/nginx/ssl
 
# Copy SSL certificates
COPY ssl/kpkapp.lan-chain.crt /etc/nginx/ssl/
COPY ssl/kpkapp.lan.key /etc/nginx/ssl/
COPY ssl/kpkapp-rootCA.crt /etc/nginx/ssl/

# Set proper permissions
RUN chmod 644 /etc/nginx/ssl/kpkapp.lan-chain.crt \
    && chmod 644 /etc/nginx/ssl/kpkapp-rootCA.crt \
    && chmod 640 /etc/nginx/ssl/kpkapp.lan.key
 
# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d
