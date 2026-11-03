# ==============================================================================
# TalentAI Frontend — Multi-Stage Production Container
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build React Production Bundle
# ------------------------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app

# Install dependencies (cached when package files are unchanged)
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Copy source code and build production assets
COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Serve Production Assets via Nginx Gateway
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine

# Remove default Nginx site configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy compiled React distribution
COPY --from=build /app/dist /usr/share/nginx/html

# Copy TalentAI reverse proxy configuration
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# Create directory for SSL certificates
RUN mkdir -p /etc/nginx/ssl

# Copy and configure TLS pre-flight entrypoint script
COPY ./nginx-entrypoint.sh /docker-entrypoint-talentai.sh
RUN chmod +x /docker-entrypoint-talentai.sh

# Standard Web Ports
EXPOSE 80 443

# Liveness health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider --no-check-certificate https://127.0.0.1/ || exit 1

ENTRYPOINT ["/docker-entrypoint-talentai.sh"]
CMD ["nginx", "-g", "daemon off;"]
