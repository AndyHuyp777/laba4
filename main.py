from flask import Flask, request, jsonify
import psycopg
import os
from urllib.parse import urlparse

app = Flask(name)

# Подключение к БД
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    conn = psycopg.connect(DATABASE_URL)
else:
    conn = None

# Создание таблицы при старте
if conn:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        conn.commit()

@app.route('/save', methods=['POST'])
def save_message():
    if not conn:
        return jsonify({"error": "DB not connected"}), 500

    data = request.get_json()
    message = data.get('message', '') if data else ''

    with conn.cursor() as cur:
        cur.execute("INSERT INTO messages (content) VALUES (%s)", (message,))
        conn.commit()

    return jsonify({"status": "saved", "message": message})

@app.route('/messages')
def get_messages():
    if not conn:
        return jsonify({"error": "DB not connected"}), 500

    with conn.cursor() as cur:
        cur.execute("SELECT id, content, created_at FROM messages ORDER BY id DESC LIMIT 10")
        rows = cur.fetchall()

    messages = [{"id": r[0], "text": r[1], "time": r[2].isoformat()} for r in rows]
    return jsonify(messages)

@app.route('/db/info')
def db_info():
    """Информация о подключении к БД"""
    if not conn:
        return jsonify({"error": "DB not connected"}), 500
    
    try:
        with conn.cursor() as cur:
            # Информация о таблицах
            cur.execute("""
                SELECT table_name, table_type 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cur.fetchall()
            
            # Количество записей в таблице messages
            cur.execute("SELECT COUNT(*) FROM messages")
            message_count = cur.fetchone()[0]
            
            return jsonify({
                "status": "connected",
                "tables": [{"name": t[0], "type": t[1]} for t in tables],
                "message_count": message_count,
                "database_url": DATABASE_URL[:20] + "..." if DATABASE_URL else None
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/db/all')
def get_all_messages():
    """Получить все сообщения из БД"""
    if not conn:
        return jsonify({"error": "DB not connected"}), 500

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, content, created_at FROM messages ORDER BY id DESC")
            rows = cur.fetchall()

        messages = [{"id": r[0], "text": r[1], "time": r[2].isoformat()} for r in rows]
        return jsonify({
            "total": len(messages),
            "messages": messages
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/db/stats')
def db_stats():
    """Статистика по базе данных"""
    if not conn:
        return jsonify({"error": "DB not connected"}), 500
    
    try:
        with conn.cursor() as cur:
            # Общее количество сообщений
            cur.execute("SELECT COUNT(*) FROM messages")
            total_messages = cur.fetchone()[0]
            
            # Последнее сообщение
            cur.execute("SELECT content, created_at FROM messages ORDER BY created_at DESC LIMIT 1")
            last_message = cur.fetchone()
            
            # Сообщения за последние 24 часа
            cur.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE created_at > NOW() - INTERVAL '24 hours'
            """)
            recent_messages = cur.fetchone()[0]
            
            return jsonify({
                "total_messages": total_messages,
                "recent_messages_24h": recent_messages,
                "last_message": {
                    "content": last_message[0] if last_message else None,
                    "time": last_message[1].isoformat() if last_message else None
                }
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)