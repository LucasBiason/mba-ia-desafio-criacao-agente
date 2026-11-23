FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN node -e 'const [major,minor]=process.versions.node.split(".").map(Number); if (!((major===22 && minor>=13)||major>=24)) process.exit(1); console.log("Frontend build Node:",process.versions.node)' \
    && npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
