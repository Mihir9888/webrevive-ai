# ==============================================================================
# WebRevive AI - Frontend Multi-Stage Dockerfile
# Stage 1: Build production React application with Node.js 20
# Stage 2: Serve static assets via hardened Nginx alpine image
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Application
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY package*.json ./
RUN npm ci || npm install

# Copy application sources
COPY . .

# Build production bundle (Vite outputs to /app/dist)
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Production Nginx Server
# ------------------------------------------------------------------------------
FROM nginx:1.25-alpine AS runner

LABEL maintainer="WebRevive AI Contributors <maintainers@webrevive.ai>"
LABEL description="WebRevive AI Frontend Web Application"

# Remove default Nginx configs
RUN rm -rf /etc/nginx/conf.d /etc/nginx/nginx.conf

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy build artifacts from builder stage (support dist or build output)
COPY --from=builder /app/dist /usr/share/nginx/html

# Adjust permissions for non-root execution
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid /var/cache/nginx /usr/share/nginx/html

USER nginx

EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
