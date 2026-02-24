"""
Dataset Import Script for Context-Aware AI Assistant
Imports all 6000 records from CSV files into Neo4j AuraDB
"""

import csv
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
import time

load_dotenv()

# ── Neo4j Connection ─────────────────────────────
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)

def run(cypher, params=None):
    with driver.session() as session:
        return session.run(cypher, params or {}).data()

# ── Helper: CSV Reader ───────────────────────────
def read_csv(filepath):
    with open(filepath, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

# ── Step 1: Import Users ─────────────────────────
def import_users(filepath):
    print("\n📥 Importing Users...")
    rows = read_csv(filepath)
    count = 0
    for row in rows:
        run("""
            MERGE (u:User {user_id: $user_id})
            SET u.name     = $name,
                u.age      = toInteger($age),
                u.city     = $city
        """, {
            "user_id": row["userId"],
            "name":    row["name"],
            "age":     row["age"],
            "city":    row["city"]
        })
        count += 1
    print(f"✅ {count} Users imported")

# ── Step 2: Import Events ────────────────────────
def import_events(filepath):
    print("\n📥 Importing Events...")
    rows = read_csv(filepath)
    count = 0
    for row in rows:
        run("""
            MATCH (u:User {user_id: $user_id})
            MERGE (e:Event {event_id: $event_id})
            SET e.title      = $title,
                e.location   = $location,
                e.start_time = $start_time
            MERGE (u)-[:HAS_EVENT]->(e)
        """, {
            "user_id":    row["userId"],
            "event_id":   row["eventId"],
            "title":      row["title"],
            "location":   row["location"],
            "start_time": row["startTime"]
        })
        count += 1
        if count % 100 == 0:
            print(f"   ...{count} events done")
    print(f"✅ {count} Events imported")

# ── Step 3: Import Reminders ─────────────────────
def import_reminders(filepath):
    print("\n📥 Importing Reminders...")
    rows = read_csv(filepath)
    count = 0
    for row in rows:
        run("""
            MATCH (u:User {user_id: $user_id})
            MERGE (r:Reminder {reminder_id: $reminder_id})
            SET r.text           = $text,
                r.scheduled_time = $scheduled_time,
                r.status         = 'pending'
            MERGE (u)-[:HAS_REMINDER]->(r)
        """, {
            "user_id":       row["userId"],
            "reminder_id":   row["reminderId"],
            "text":          row["text"],
            "scheduled_time": row["scheduledTime"]
        })
        count += 1
        if count % 100 == 0:
            print(f"   ...{count} reminders done")
    print(f"✅ {count} Reminders imported")

# ── Step 4: Import Tasks ─────────────────────────
def import_tasks(filepath):
    print("\n📥 Importing Tasks...")
    rows = read_csv(filepath)
    count = 0
    for row in rows:
        run("""
            MATCH (u:User {user_id: $user_id})
            MERGE (t:Task {task_id: $task_id})
            SET t.title    = $title,
                t.priority = $priority,
                t.status   = $status
            MERGE (u)-[:HAS_TASK]->(t)
        """, {
            "user_id": row["userId"],
            "task_id": row["taskId"],
            "title":   row["title"],
            "priority": row["priority"],
            "status":  row["status"]
        })
        count += 1
        if count % 100 == 0:
            print(f"   ...{count} tasks done")
    print(f"✅ {count} Tasks imported")

# ── Step 5: Import Time Contexts ─────────────────
def import_time_contexts(filepath):
    print("\n📥 Importing Time Contexts...")
    rows = read_csv(filepath)
    count = 0
    for row in rows:
        run("""
            MERGE (tc:TimeContext {time_id: $time_id})
            SET tc.day_type = $day_type,
                tc.period   = $period
        """, {
            "time_id":  row["timeId"],
            "day_type": row["dayType"],
            "period":   row["period"]
        })
        count += 1
    print(f"✅ {count} Time Contexts imported")

# ── Step 6: Create Schema Indexes ────────────────
def create_indexes():
    print("\n📥 Creating indexes for fast queries...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.city)",
        "CREATE INDEX IF NOT EXISTS FOR (u:User) ON (u.name)",
        "CREATE INDEX IF NOT EXISTS FOR (t:Task) ON (t.status)",
        "CREATE INDEX IF NOT EXISTS FOR (t:Task) ON (t.priority)",
        "CREATE INDEX IF NOT EXISTS FOR (r:Reminder) ON (r.scheduled_time)",
        "CREATE INDEX IF NOT EXISTS FOR (e:Event) ON (e.start_time)",
        "CREATE INDEX IF NOT EXISTS FOR (tc:TimeContext) ON (tc.day_type)",
    ]
    for idx in indexes:
        run(idx)
    print("✅ Indexes created")

# ── Step 7: Verify Import ────────────────────────
def verify():
    print("\n🔍 Verifying import...")
    counts = run("""
        MATCH (u:User)     WITH count(u) AS users
        MATCH (e:Event)    WITH users, count(e) AS events
        MATCH (r:Reminder) WITH users, events, count(r) AS reminders
        MATCH (t:Task)     WITH users, events, reminders, count(t) AS tasks
        MATCH (tc:TimeContext) 
        RETURN users, events, reminders, tasks, count(tc) AS timecontexts
    """)
    if counts:
        c = counts[0]
        print(f"""
╔══════════════════════════════════╗
║       NEO4J IMPORT SUMMARY       ║
╠══════════════════════════════════╣
║  Users        : {str(c['users']).ljust(17)} ║
║  Events       : {str(c['events']).ljust(17)} ║
║  Reminders    : {str(c['reminders']).ljust(17)} ║
║  Tasks        : {str(c['tasks']).ljust(17)} ║
║  Time Contexts: {str(c['timecontexts']).ljust(17)} ║
╚══════════════════════════════════╝
        """)

# ── MAIN ─────────────────────────────────────────
if __name__ == "__main__":
    BASE = r"C:\Users\Welcome\OneDrive\Desktop\assistant\backend\datasets"

    start = time.time()
    print("🚀 Starting dataset import into Neo4j...\n")

    create_indexes()
    import_users(      f"{BASE}\\bigdata_users_300.csv")
    import_events(     f"{BASE}\\context_events_1000.csv")
    import_reminders(  f"{BASE}\\context_reminders_1200.csv")
    import_tasks(      f"{BASE}\\context_tasks_1500.csv")
    import_time_contexts(f"{BASE}\\context_timecontext_2000.csv")
    verify()

    elapsed = round(time.time() - start, 2)
    print(f"⏱️  Total import time: {elapsed} seconds")
    print("🎉 All data imported successfully into Neo4j!")

    driver.close()