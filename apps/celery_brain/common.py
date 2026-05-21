import psycopg2

from confluent_kafka import Producer

from common.config import AppConfig



def get_db_connection():
    return psycopg2.connect(
        host=AppConfig.DB_HOST,
        database=AppConfig.DB_NAME,
        user=AppConfig.DB_USER,
        password=AppConfig.DB_PASS
    )

# Fonction de callback optionnelle (mais recommandée en indus) pour vérifier que le message est bien parti
def delivery_report(err, msg):
    if err is not None:
        print(f"❌ Échec de l'envoi Kafka : {err}")
    else:
        print(f"✅ Ordre livré sur {msg.topic()} [{msg.partition()}]")



