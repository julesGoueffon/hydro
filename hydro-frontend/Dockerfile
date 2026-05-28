# Étape 1 : Compilation (Build)
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# Étape 2 : Serveur Web Ultra-Léger (Production)
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# Injection propre de la configuration Nginx (sans erreur de variable)
COPY default.conf /etc/nginx/conf.d/default.conf


EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]