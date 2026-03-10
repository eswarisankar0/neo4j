from flask import Flask, request, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "password"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def s():
    return driver.session()

def now():
    return datetime.utcnow().isoformat()

def serialize(obj):
    result = {}
    for key, value in dict(obj).items():
        if hasattr(value, 'isoformat'):
            result[key] = value.isoformat()
        elif type(value).__module__ == 'neo4j.time':
            result[key] = str(value)
        else:
            result[key] = value
    return result

def init_db():
    with s() as session:
        session.run("CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE")
        session.run("CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE")
        session.run("CREATE CONSTRAINT conv_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE")
        session.run("CREATE CONSTRAINT mem_id  IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE")
        session.run("CREATE CONSTRAINT pref_id IF NOT EXISTS FOR (p:Preference) REQUIRE p.id IS UNIQUE")
    print("Neo4j constraints ready")

@app.route("/api/user", methods=["POST"])
def create_user():
    d = request.json
    uid = str(uuid.uuid4())
    with s() as session:
        session.run(
            "CREATE (u:User {id:$id, name:$name, email:$email, createdAt:$ts})",
            id=uid, name=d["name"], email=d.get("email",""), ts=now()
        )
    return jsonify({"id": uid, "name": d["name"]})

@app.route("/api/user/<uid>", methods=["GET"])
def get_user(uid):
    with s() as session:
        r = session.run("MATCH (u:User {id:$id}) RETURN u", id=uid).single()
        if not r:
            return jsonify({"error": "User not found"}), 404
        return jsonify(serialize(r["u"]))

@app.route("/api/user/<uid>/preferences", methods=["GET"])
def get_preferences(uid):
    with s() as session:
        rows = session.run(
            "MATCH (u:User {id:$id})-[:HAS_PREFERENCE]->(p:Preference) RETURN p", id=uid
        )
        return jsonify([serialize(r["p"]) for r in rows])

@app.route("/api/user/<uid>/preferences", methods=["POST"])
def set_preference(uid):
    d = request.json
    pid = str(uuid.uuid4())
    with s() as session:
        session.run(
            "MATCH (u:User {id:$uid})-[r:HAS_PREFERENCE]->(p:Preference {category:$cat}) DELETE r, p",
            uid=uid, cat=d["category"]
        )
        session.run(
            """MATCH (u:User {id:$uid})
               CREATE (p:Preference {id:$id, category:$cat, value:$val, updatedAt:$ts})
               CREATE (u)-[:HAS_PREFERENCE]->(p)""",
            uid=uid, id=pid, cat=d["category"], val=d["value"], ts=now()
        )
    return jsonify({"id": pid, "category": d["category"], "value": d["value"]})

@app.route("/api/user/<uid>/tasks", methods=["GET"])
def get_tasks(uid):
    with s() as session:
        rows = session.run(
            "MATCH (u:User {id:$id})-[:HAS_TASK]->(t:Task) RETURN t ORDER BY t.createdAt DESC",
            id=uid
        )
        return jsonify([serialize(r["t"]) for r in rows])

@app.route("/api/user/<uid>/tasks", methods=["POST"])
def create_task(uid):
    d = request.json
    tid = str(uuid.uuid4())
    with s() as session:
        session.run(
            """MATCH (u:User {id:$uid})
               CREATE (t:Task {id:$id, title:$title, status:'pending',
                               priority:$priority, dueDate:$due, createdAt:$ts})
               CREATE (u)-[:HAS_TASK]->(t)""",
            uid=uid, id=tid, title=d["title"],
            priority=d.get("priority","medium"), due=d.get("dueDate",""), ts=now()
        )
    return jsonify({"id": tid, "title": d["title"], "status": "pending"})

@app.route("/api/task/<tid>", methods=["PUT"])
def update_task(tid):
    d = request.json
    with s() as session:
        session.run("MATCH (t:Task {id:$id}) SET t.status=$status", id=tid, status=d["status"])
    return jsonify({"updated": True})

@app.route("/api/task/<tid>", methods=["DELETE"])
def delete_task(tid):
    with s() as session:
        session.run("MATCH (t:Task {id:$id}) DETACH DELETE t", id=tid)
    return jsonify({"deleted": True})

@app.route("/api/user/<uid>/memory", methods=["GET"])
def get_memory(uid):
    with s() as session:
        rows = session.run(
            "MATCH (u:User {id:$id})-[:REMEMBERS]->(m:Memory) RETURN m ORDER BY m.createdAt DESC",
            id=uid
        )
        return jsonify([serialize(r["m"]) for r in rows])

@app.route("/api/user/<uid>/memory", methods=["POST"])
def add_memory(uid):
    d = request.json
    mid = str(uuid.uuid4())
    with s() as session:
        session.run(
            """MATCH (u:User {id:$uid})
               CREATE (m:Memory {id:$id, type:$type, content:$content, createdAt:$ts})
               CREATE (u)-[:REMEMBERS]->(m)""",
            uid=uid, id=mid, type=d.get("type","fact"), content=d["content"], ts=now()
        )
    return jsonify({"id": mid, "content": d["content"]})

@app.route("/api/memory/<mid>", methods=["DELETE"])
def delete_memory(mid):
    with s() as session:
        session.run("MATCH (m:Memory {id:$id}) DETACH DELETE m", id=mid)
    return jsonify({"deleted": True})

@app.route("/api/user/<uid>/conversations", methods=["GET"])
def get_conversations(uid):
    with s() as session:
        rows = session.run(
            """MATCH (u:User {id:$id})-[:HAD_CONVERSATION]->(c:Conversation)
               RETURN c ORDER BY c.timestamp DESC LIMIT 50""", id=uid
        )
        return jsonify([serialize(r["c"]) for r in rows])

@app.route("/api/user/<uid>/chat", methods=["POST"])
def chat(uid):
    d = request.json
    user_msg = d["message"]
    cid = str(uuid.uuid4())

    with s() as session:
        user_row  = session.run("MATCH (u:User {id:$id}) RETURN u", id=uid).single()
        user_name = serialize(user_row["u"])["name"] if user_row else "User"
        memories  = [r["c"] for r in session.run(
            "MATCH (u:User {id:$id})-[:REMEMBERS]->(m:Memory) RETURN m.content AS c LIMIT 5", id=uid)]
        tasks     = [r["t"] for r in session.run(
            "MATCH (u:User {id:$id})-[:HAS_TASK]->(t:Task {status:'pending'}) RETURN t.title AS t LIMIT 5", id=uid)]
        prefs     = {r["k"]: r["v"] for r in session.run(
            "MATCH (u:User {id:$id})-[:HAS_PREFERENCE]->(p:Preference) RETURN p.category AS k, p.value AS v", id=uid)}

    msg_lower = user_msg.lower()
    bot_reply = generate_reply(user_name, user_msg, msg_lower, memories, tasks, prefs)

    if any(kw in msg_lower for kw in ["remind me","add task","create task","don't forget","todo","we have to","i have to","i need to","tomorrow","meeting","show","submit","deadline"]):
        with s() as session:
            session.run(
                """MATCH (u:User {id:$uid})
                   CREATE (t:Task {id:$id, title:$title, status:'pending',
                                   priority:'medium', dueDate:'', createdAt:$ts})
                   CREATE (u)-[:HAS_TASK]->(t)""",
                uid=uid, id=str(uuid.uuid4()), title=user_msg[:80], ts=now()
            )

    if any(kw in msg_lower for kw in ["i always","i usually","i prefer","i like","i wake","i love","i enjoy","i hate","i drink","i eat","i read","i watch"]):
        with s() as session:
            session.run(
                """MATCH (u:User {id:$uid})
                   CREATE (m:Memory {id:$id, type:'habit', content:$content, createdAt:$ts})
                   CREATE (u)-[:REMEMBERS]->(m)""",
                uid=uid, id=str(uuid.uuid4()), content=user_msg[:120], ts=now()
            )

    with s() as session:
        session.run(
            """MATCH (u:User {id:$uid})
               CREATE (c:Conversation {id:$id, userMessage:$um, botReply:$br, timestamp:$ts})
               CREATE (u)-[:HAD_CONVERSATION]->(c)""",
            uid=uid, id=cid, um=user_msg, br=bot_reply, ts=now()
        )

    return jsonify({"reply": bot_reply, "conversationId": cid})


def generate_reply(name, original, msg, memories, tasks, prefs):
    mem_ctx  = "; ".join(memories[:3]) if memories else "none"
    task_ctx = ", ".join(tasks[:3])    if tasks    else "none"

    if any(k in msg for k in ["hello","hi","hey"]):
        task_hint = f" You have {len(tasks)} pending task(s)." if tasks else ""
        return f"Hello {name}! 👋 Good to see you.{task_hint} How can I help?"

    if any(k in msg for k in ["remind","add task","todo","create task"]):
        return f"Got it {name}! Added to your tasks. Pending: {task_ctx or 'none yet'}."

    if any(k in msg for k in ["memory","remember"]):
        return f"Sure {name}, I'll remember that! I currently know: {mem_ctx}."

    if any(k in msg for k in ["prefer","setting"]):
        p_str = ", ".join(f"{k}={v}" for k,v in prefs.items()) if prefs else "none set"
        return f"Your preferences: {p_str}."

    if any(k in msg for k in ["what do you know","context","about me"]):
        return f"Here's what I know about you, {name}: {mem_ctx}. Pending tasks: {task_ctx}."

    if any(k in msg for k in ["bye","goodbye","see you"]):
        return f"Goodbye {name}! Everything is saved in Neo4j. See you next time! 👋"

    if memories:
        return f"Got it, {name}! I've noted that down.  Anything else I can help with?"
    return f"Sure, {name}! Noted. Is there anything else?"


@app.route("/api/user/<uid>/stats", methods=["GET"])
def get_stats(uid):
    with s() as session:
        tc = session.run("MATCH (u:User {id:$id})-[:HAS_TASK]->(t) RETURN count(t) AS c", id=uid).single()["c"]
        pc = session.run("MATCH (u:User {id:$id})-[:HAS_TASK]->(t {status:'pending'}) RETURN count(t) AS c", id=uid).single()["c"]
        mc = session.run("MATCH (u:User {id:$id})-[:REMEMBERS]->(m) RETURN count(m) AS c", id=uid).single()["c"]
        cc = session.run("MATCH (u:User {id:$id})-[:HAD_CONVERSATION]->(c) RETURN count(c) AS c", id=uid).single()["c"]
    return jsonify({"totalTasks":tc, "pendingTasks":pc, "memories":mc, "conversations":cc})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)