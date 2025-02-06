FROM nginx:1.21-alpine
 
# Remove default config
RUN rm /etc/nginx/conf.d/default.conf
 
# Create SSL directory
RUN mkdir -p /etc/nginx/ssl
 
# Copy SSL certificates
COPY ssl/exceladdin.crt /etc/nginx/ssl/
COPY ssl/exceladdin.key /etc/nginx/ssl/
 
# Set proper permissions
RUN chmod 644 /etc/nginx/ssl/exceladdin.crt \
    && chmod 640 /etc/nginx/ssl/exceladdin.key
 
# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d