FROM node:22.23.3-slim@sha256:3ed98443660ff48413b5af19ecefce3b9d50845a901a43420d47cc63a9fddbe9
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY index.html vite.config.ts vitest.config.ts tsconfig*.json ./
COPY src ./src
EXPOSE 5173
