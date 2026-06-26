# --- Этап 1: сборка фронтенда ---
FROM node:20-alpine AS build

WORKDIR /app

# Сначала зависимости (для кэширования слоёв)
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Исходники и сборка
COPY . .
RUN npm run build

# --- Этап 2: раздача статики через Nginx ---
FROM nginx:1.27-alpine

# Конфигурация Nginx (SPA + реверс-прокси на /api)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Собранные статические файлы
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
