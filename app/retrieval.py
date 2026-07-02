

import os
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
EMBED_MODEL  = "BAAI/bge-base-en-v1.5"

# Load once at module level so it isn't reloaded on every API call
embedder = SentenceTransformer(EMBED_MODEL)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def embed_query(text):
    """BGE models work best with this prefix for retrieval queries."""
    prefixed = f"Represent this sentence for searching relevant passages: {text}"
    vector = embedder.encode(prefixed, normalize_embeddings=True)
    return vector.tolist()


def retrieve(query, top_k=5, subject=None, topic_names=None):
    """
    Retrieves the top_k most relevant syllabus chunks for a query.

    Args:
        query       (str)       : Student's question or topic string.
        top_k       (int)       : Number of chunks to return.
        subject     (str|None)  : Filter by subject e.g. "Physics".
        topic_names (list|None) : Filter by topic names e.g. ["Electrochemistry"].

    Returns:
        list of dicts with keys: chunk_id, subject, topic, chunk_text, distance
    """
    query_vector = embed_query(query)

    filters = []
    params  = []

    if subject:
        filters.append("t.subject = %s")
        params.append(subject)

    if topic_names:
        placeholders = ", ".join(["%s"] * len(topic_names))
        filters.append(f"t.name IN ({placeholders})")
        params.extend(topic_names)

    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

    sql = f"""
        SELECT
            sc.chunk_id,
            t.subject,
            t.name       AS topic,
            sc.chunk_text,
            sc.embedding <=> %s::vector AS distance
        FROM syllabus_chunks sc
        JOIN topics t ON sc.topic_id = t.topic_id
        {where_clause}
        ORDER BY distance ASC
        LIMIT %s;
    """

    all_params = [str(query_vector)] + params + [top_k]

    conn = get_connection()
    cur  = conn.cursor()
    cur.execute(sql, all_params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "chunk_id"   : row[0],
            "subject"    : row[1],
            "topic"      : row[2],
            "chunk_text" : row[3],
            "distance"   : round(row[4], 4),
        }
        for row in rows
    ]


def retrieve_for_weak_topics(student_id, top_k_per_topic=3):
    """
    Flow B: fetches a student's weak topics and retrieves
    relevant syllabus chunks for each one.

    Returns:
        dict: { "topic_name": [chunks, ...], ... }
    """
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT DISTINCT t.name, t.subject
        FROM student_weak_topics swt
        JOIN topics t ON swt.topic_id = t.topic_id
        WHERE swt.student_id = %s
        ORDER BY t.subject, t.name;
    """, (student_id,))
    weak_topics = cur.fetchall()
    cur.close()
    conn.close()

    if not weak_topics:
        return {}

    results = {}
    for topic_name, subject in weak_topics:
        chunks = retrieve(
            query=topic_name,
            top_k=top_k_per_topic,
            subject=subject,
            topic_names=[topic_name]
        )
        results[topic_name] = chunks

    return results