import psycopg2

from confluent_kafka import Producer

from common.config import AppConfig
from celery import Celery


# Configuration Celery
app = Celery('hydro_brain', broker=AppConfig.REDIS_URL)



kafka_conf = {
    'bootstrap.servers': AppConfig.KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'hydro_brain_worker',
}

# Initialisation
# Variable globale vide au départ
_kafka_producer = None


def get_kafka_producer():
    """Crée le producer uniquement quand on en a besoin, à l'intérieur du worker."""
    global _kafka_producer
    if _kafka_producer is None:
        # On ajoute le PID (Process ID) pour que chaque worker ait son propre ID propre
        conf = kafka_conf.copy()
        conf['client.id'] = f"hydro_brain_worker_{os.getpid()}"
        _kafka_producer = Producer(conf)
        print(f"✅ Nouveau Kafka Producer créé pour le worker {os.getpid()}")

    return _kafka_producer

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
