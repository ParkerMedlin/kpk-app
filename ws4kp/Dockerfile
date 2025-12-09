FROM node:24-alpine AS node-builder
WORKDIR /app

COPY package.json .
COPY package-lock.json .
COPY . .

RUN npm install --legacy-peer-deps
RUN npm run build
RUN rm dist/playlist.json

FROM nginx:alpine

COPY static-env-handler.sh /docker-entrypoint.d/01-static-env-handler.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/01-static-env-handler.sh && chmod +x /docker-entrypoint.d/01-static-env-handler.sh

COPY --from=node-builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
CMD ["nginx", "-g", "daemon off;"]
