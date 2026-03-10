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


# ── USER ──────────────────────────────────────────────────────────

@app.route("/api/user", methods=["POST"])
def create_user():
    d = request.json
    uid = str(uuid.uuid4())
    with s() as session:
        # CREATE node
        session.run(
            "CREATE (u:User {id:$id, name:$name, email:$email, createdAt:$ts})",
            id=uid, name=d["name"], email=d.get("email",""), ts=now()
        )
    return jsonify({"id": uid, "name": d["name"]})

@app.route("/api/user/<uid>", methods=["GET"])
def get_user(uid):
    with s() as session:
        # MATCH + RETURN
        r = session.run("MATCH (u:User {id:$id}) RETURN u", id=uid).single()
        if not r:
            return jsonify({"error": "User not found"}), 404
        return jsonify(serialize(r["u"]))


# ── PREFERENCES ───────────────────────────────────────────────────

@app.route("/api/user/<uid>/preferences", methods=["GET"])
def get_preferences(uid):
    with s() as session:
        # MATCH + RETURN with ORDER BY
        rows = session.run(
            """MATCH (u:User {id:$id})-[:HAS_PREFERENCE]->(p:Preference)
               RETURN p ORDER BY p.category""",
            id=uid
        )
        return jsonify([serialize(r["p"]) for r in rows])

@app.route("/api/user/<uid>/preferences", methods=["POST"])
def set_preference(uid):
    d = request.json
    pid = str(uuid.uuid4())
    with s() as session:
        # DELETE old preference of same category
        session.run(
            """MATCH (u:User {id:$uid})-[r:HAS_PREFERENCE]->(p:Preference {category:$cat})
               DELETE r, p""",
            uid=uid, cat=d["category"]
        )
        # CREATE new preference node + relationship
        session.run(
            """MATCH (u:User {id:$uid})
               CREATE (p:Preference {id:$id, category:$cat, value:$val, updatedAt:$ts})
               CREATE (u)-[:HAS_PREFERENCE]->(p)""",
            uid=uid, id=pid, cat=d["category"], val=d["value"], ts=now()
        )
    return jsonify({"id": pid, "category": d["category"], "value": d["value"]})


# ── TASKS ─────────────────────────────────────────────────────────

@app.route("/api/user/<uid>/tasks", methods=["GET"])
def get_tasks(uid):
    with s() as session:
        # MATCH + RETURN + ORDER BY
        rows = session.run(
            """MATCH (u:User {id:$id})-[:HAS_TASK]->(t:Task)
               RETURN t ORDER BY t.createdAt DESC""",
            id=uid
        )
        return jsonify([serialize(r["t"]) for r in rows])

@app.route("/api/user/<uid>/tasks", methods=["POST"])
def create_task(uid):
    d = request.json
    tid = str(uuid.uuid4())
    with s() as session:
        # CREATE task node + relationship
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
        # SET to update property
        session.run(
            "MATCH (t:Task {id:$id}) SET t.status=$status, t.updatedAt=$ts",
            id=tid, status=d["status"], ts=now()
        )
    return jsonify({"updated": True})

@app.route("/api/task/<tid>", methods=["DELETE"])
def delete_task(tid):
    with s() as session:
        # DETACH DELETE node
        session.run("MATCH (t:Task {id:$id}) DETACH DELETE t", id=tid)
    return jsonify({"deleted": True})

@app.route("/api/task/<tid>/remove-due", methods=["PUT"])
def remove_due_date(tid):
    with s() as session:
        # REMOVE property from node
        session.run(
            "MATCH (t:Task {id:$id}) REMOVE t.dueDate RETURN t",
            id=tid
        )
    return jsonify({"removed": "dueDate"})

@app.route("/api/user/<uid>/tasks/complete-all", methods=["PUT"])
def complete_all_tasks(uid):
    with s() as session:
        # FOREACH to update all nodes in a collection
        session.run(
            """MATCH (u:User {id:$uid})-[:HAS_TASK]->(t:Task {status:'pending'})
               WITH collect(t) AS tasks
               FOREACH (t IN tasks | SET t.status = 'completed', t.completedAt = $ts)""",
            uid=uid, ts=now()
        )
    return jsonify({"completed": True})


# ── MEMORY ────────────────────────────────────────────────────────

@app.route("/api/user/<uid>/memory", methods=["GET"])
def get_memory(uid):
    with s() as session:
        # MATCH + RETURN + ORDER BY + LIMIT
        rows = session.run(
            """MATCH (u:User {id:$id})-[:REMEMBERS]->(m:Memory)
               RETURN m ORDER BY m.createdAt DESC LIMIT 20""",
            id=uid
        )
        return jsonify([serialize(r["m"]) for r in rows])

@app.route("/api/user/<uid>/memory", methods=["POST"])
def add_memory(uid):
    d = request.json
    mid = str(uuid.uuid4())
    with s() as session:
        # CREATE memory node + relationship
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
        # DETACH DELETE
        session.run("MATCH (m:Memory {id:$id}) DETACH DELETE m", id=mid)
    return jsonify({"deleted": True})

@app.route("/api/memory/<mid>/remove-type", methods=["PUT"])
def remove_memory_type(mid):
    with s() as session:
        # REMOVE label property
        session.run(
            "MATCH (m:Memory {id:$id}) REMOVE m.type RETURN m",
            id=mid
        )
    return jsonify({"removed": "type"})


# ── CONVERSATION ──────────────────────────────────────────────────

@app.route("/api/user/<uid>/conversations", methods=["GET"])
def get_conversations(uid):
    skip = request.args.get("skip", 0, type=int)
    with s() as session:
        # MATCH + ORDER BY + SKIP + LIMIT
        rows = session.run(
            """MATCH (u:User {id:$id})-[:HAD_CONVERSATION]->(c:Conversation)
               RETURN c ORDER BY c.timestamp DESC SKIP $skip LIMIT 50""",
            id=uid, skip=skip
        )
        return jsonify([serialize(r["c"]) for r in rows])

@app.route("/api/user/<uid>/chat", methods=["POST"])
def chat(uid):
    d = request.json
    user_msg = d["message"]
    cid = str(uuid.uuid4())

    with s() as session:
        # MATCH user
        user_row  = session.run("MATCH (u:User {id:$id}) RETURN u", id=uid).single()
        user_name = serialize(user_row["u"])["name"] if user_row else "User"

        # MATCH memories with LIMIT
        memories = [r["c"] for r in session.run(
            """MATCH (u:User {id:$id})-[:REMEMBERS]->(m:Memory)
               RETURN m.content AS c LIMIT 5""", id=uid)]

        # MATCH pending tasks with WHERE
        tasks = [r["t"] for r in session.run(
            """MATCH (u:User {id:$id})-[:HAS_TASK]->(t:Task)
               WHERE t.status = 'pending'
               RETURN t.title AS t LIMIT 5""", id=uid)]

        # MATCH preferences
        prefs = {r["k"]: r["v"] for r in session.run(
            """MATCH (u:User {id:$id})-[:HAS_PREFERENCE]->(p:Preference)
               RETURN p.category AS k, p.value AS v""", id=uid)}

        # WITH clause — count tasks and memories for context
        counts = session.run(
            """MATCH (u:User {id:$id})
               OPTIONAL MATCH (u)-[:HAS_TASK]->(t:Task {status:'pending'})
               WITH u, count(t) AS pendingCount
               OPTIONAL MATCH (u)-[:REMEMBERS]->(m:Memory)
               WITH u, pendingCount, count(m) AS memCount
               RETURN pendingCount, memCount""",
            id=uid
        ).single()
        pending_count = counts["pendingCount"] if counts else 0
        mem_count     = counts["memCount"]     if counts else 0

    msg_lower = user_msg.lower()
    bot_reply = generate_reply(user_name, user_msg, msg_lower, memories, tasks, prefs, pending_count, mem_count)

    # Auto-create Task node if message implies a task
    if any(kw in msg_lower for kw in ["remind me","add task","create task","don't forget",
                                       "todo","we have to","i have to","i need to",
                                       "tomorrow","meeting","show","submit","deadline"]):
        with s() as session:
            # CREATE task + SET label
            session.run(
                """MATCH (u:User {id:$uid})
                   CREATE (t:Task {id:$id, title:$title, status:'pending',
                                   priority:'medium', dueDate:'', createdAt:$ts})
                   SET t:AutoCreated
                   CREATE (u)-[:HAS_TASK]->(t)""",
                uid=uid, id=str(uuid.uuid4()), title=user_msg[:80], ts=now()
            )

    # Auto-store Memory node if message implies a habit/preference
    if any(kw in msg_lower for kw in ["i always","i usually","i prefer","i like",
                                       "i wake","i love","i enjoy","i hate",
                                       "i drink","i eat","i read","i watch"]):
        with s() as session:
            # CREATE memory node
            session.run(
                """MATCH (u:User {id:$uid})
                   CREATE (m:Memory {id:$id, type:'habit', content:$content, createdAt:$ts})
                   CREATE (u)-[:REMEMBERS]->(m)""",
                uid=uid, id=str(uuid.uuid4()), content=user_msg[:120], ts=now()
            )

    # Save conversation node
    with s() as session:
        session.run(
            """MATCH (u:User {id:$uid})
               CREATE (c:Conversation {id:$id, userMessage:$um, botReply:$br, timestamp:$ts})
               CREATE (u)-[:HAD_CONVERSATION]->(c)""",
            uid=uid, id=cid, um=user_msg, br=bot_reply, ts=now()
        )

    return jsonify({"reply": bot_reply, "conversationId": cid})


# ── STATS — uses WITH to chain counts ─────────────────────────────

@app.route("/api/user/<uid>/stats", methods=["GET"])
def get_stats(uid):
    with s() as session:
        # WITH clause chaining multiple counts
        result = session.run(
            """MATCH (u:User {id:$id})
               OPTIONAL MATCH (u)-[:HAS_TASK]->(t:Task)
               WITH u, count(t) AS totalTasks
               OPTIONAL MATCH (u)-[:HAS_TASK]->(pt:Task {status:'pending'})
               WITH u, totalTasks, count(pt) AS pendingTasks
               OPTIONAL MATCH (u)-[:REMEMBERS]->(m:Memory)
               WITH u, totalTasks, pendingTasks, count(m) AS memories
               OPTIONAL MATCH (u)-[:HAD_CONVERSATION]->(c:Conversation)
               RETURN totalTasks, pendingTasks, memories, count(c) AS conversations""",
            id=uid
        ).single()
        return jsonify({
            "totalTasks":    result["totalTasks"],
            "pendingTasks":  result["pendingTasks"],
            "memories":      result["memories"],
            "conversations": result["conversations"]
        })


# ── UNION — combine tasks + memories in one query ─────────────────

@app.route("/api/user/<uid>/activity", methods=["GET"])
def get_activity(uid):
    with s() as session:
        # UNION to combine two different node types
        rows = session.run(
            """MATCH (u:User {id:$id})-[:HAS_TASK]->(t:Task)
               RETURN t.title AS content, 'task' AS type, t.createdAt AS createdAt
               UNION
               MATCH (u:User {id:$id})-[:REMEMBERS]->(m:Memory)
               RETURN m.content AS content, 'memory' AS type, m.createdAt AS createdAt""",
            id=uid
        )
        results = []
        for r in rows:
            item = {"content": r["content"], "type": r["type"]}
            val  = r["createdAt"]
            item["createdAt"] = val.isoformat() if hasattr(val,"isoformat") else str(val)
            results.append(item)
        return jsonify(results)


# ── FOREACH — mark all tasks in path as highlighted ───────────────

@app.route("/api/user/<uid>/tasks/highlight", methods=["PUT"])
def highlight_tasks(uid):
    with s() as session:
        # FOREACH to iterate over collected nodes
        session.run(
            """MATCH (u:User {id:$uid})-[:HAS_TASK]->(t:Task)
               WITH collect(t) AS tasks
               FOREACH (t IN tasks | SET t.highlighted = true)""",
            uid=uid
        )
    return jsonify({"highlighted": True})


def generate_reply(name, original, msg, memories, tasks, prefs, pending_count, mem_count):
    mem_ctx = "; ".join(memories[:3]) if memories else "none"

    if any(k in msg for k in ["hello","hi","hey"]):
        return f"Hello {name}! You have {pending_count} pending task(s) and {mem_count} memories stored. How can I help?"

    if any(k in msg for k in ["remind","add task","todo","create task","we have","i have to","i need","tomorrow","meeting","submit","deadline"]):
        return f"Noted, {name}. Task saved."

    if any(k in msg for k in ["i always","i usually","i prefer","i like","i wake","i love","i enjoy","i hate","i drink","i eat","i read","i watch"]):
        return f"Noted, {name}. I'll remember that."

    if any(k in msg for k in ["memory","remember"]):
        return f"I currently remember: {mem_ctx}."

    if any(k in msg for k in ["prefer","setting"]):
        p_str = ", ".join(f"{k}={v}" for k,v in prefs.items()) if prefs else "none set"
        return f"Your preferences: {p_str}."

    if any(k in msg for k in ["what do you know","context","about me"]):
        return f"Here is what I know about you, {name}: {mem_ctx}."

    if any(k in msg for k in ["bye","goodbye","see you"]):
        return f"Goodbye {name}. See you next time."

    return f"Noted, {name}."

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5001)
