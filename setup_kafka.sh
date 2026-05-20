#!/bin/bash

echo "⏳ Attente du démarrage de Redpanda..."

# On boucle tant que rpk ne renvoie pas un succès
while ! rpk cluster info --brokers redpanda:9092 > /dev/null 2>&1; do
  echo "Redpanda pas encore prêt, on patiente 2s..."
  sleep 2
done

echo "🚀 Redpanda est en ligne ! Création des topics..."
rpk topic create telemetry_stream actuator_stream command_stream image_events weather_raw --brokers redpanda:9092

echo "✅ Topics provisionnés avec succès !"