# Use an official Node.js runtime as the build stage
FROM node:20-alpine AS builder
WORKDIR /app

# Accept build argument for backend API URL
ARG BACKEND_API_URL
ENV BACKEND_API_URL=$BACKEND_API_URL

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy the source code and build the app
COPY . .
RUN npm run build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Copy built files and dependencies
COPY --from=builder /app/package.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next

EXPOSE 3000

CMD ["npm", "start"]
