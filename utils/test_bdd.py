import psycopg2

try:
    conn = psycopg2.connect(
        host="localhost",
        database="greenhouse",
        user="admin",
        password="password"
    )
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM weather_metrics;")
    count = cur.fetchone()[0]
    print(f"📊 Nombre de lignes dans la table : {count}")

    if count > 0:
        cur.execute("SELECT * FROM weather_metrics LIMIT 5;")
        rows = cur.fetchall()
        for row in rows:
            print(row)

    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ Erreur de connexion : {e}")