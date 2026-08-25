# NODEJS TEMPLATE

# syntax=docker/dockerfile:1
# https://docs.docker.com/develop/develop-images/multistage-build/

ARG NODE_VERSION=20-slim

# BASE
FROM node:$NODE_VERSION AS base

WORKDIR /app

COPY ../package.json ../package-lock.json ./

RUN npm install

# BUILD
FROM base AS build

WORKDIR /app

COPY . .

COPY --chown=node:node --from=base /app/node_modules ./node_modules

RUN npm run build

# RUNTIME
FROM node:$NODE_VERSION

WORKDIR /app

COPY --chown=node:node --from=build /app/package.json /app/package-lock.json ./
COPY --chown=node:node --from=build /app/node_modules ./node_modules
COPY --chown=node:node --from=build /app/dist ./dist

RUN npm prune --production && npm cache clean -f

EXPOSE 8080

USER node

CMD ["node", "dist/index.js"]
