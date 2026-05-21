FROM searxng/searxng:latest

# Копируем наш settings.yml внутрь образа.
# fly.io volume монтируется в /etc/searxng — но при первом старте
# volume пустой, поэтому вшиваем конфиг в образ как fallback.
# SearXNG читает /etc/searxng/settings.yml при старте.
COPY settings.yml /etc/searxng/settings.yml

# Права — SearXNG запускается от пользователя searxng
RUN chown searxng:searxng /etc/searxng/settings.yml

EXPOSE 8080