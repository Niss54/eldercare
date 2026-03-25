# Multi-stage build for Next.js
FROM node:20-alpine AS builder

WORKDIR /build

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Build Next.js app
COPY . .
RUN npm run build


# Runtime image
FROM node:20-alpine

WORKDIR /app

# Install production dependencies only
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps --only=production && \
    npm cache clean --force

# Copy built application
COPY --from=builder /build/.next /app/.next
COPY --from=builder /build/public /app/public
COPY next.config.js ./

# Create non-root user for security
RUN addgroup -g 1000 nextjs && adduser -u 1000 -G nextjs -S nextjs
USER nextjs

# Expose port
EXPOSE 3000

# Environment variables
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000', (r) => {if (r.statusCode !== 200) throw new Error(r.statusCode)})"

# Start application
CMD ["node_modules/.bin/next", "start"]
