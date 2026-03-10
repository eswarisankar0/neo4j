// ── Constraints ──────────────────────────────────────────
CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User)         REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT task_id IF NOT EXISTS FOR (t:Task)         REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT conv_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT mem_id  IF NOT EXISTS FOR (m:Memory)       REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT pref_id IF NOT EXISTS FOR (p:Preference)   REQUIRE p.id IS UNIQUE;

// ── Sample User ───────────────────────────────────────────
CREATE (u:User {
  id: "user-001",
  name: "Alex",
  email: "alex@example.com",
  createdAt: datetime()
});

// ── Sample Preferences ────────────────────────────────────
CREATE (p1:Preference { id: "pref-001", category: "theme",    value: "dark",    updatedAt: datetime() });
CREATE (p2:Preference { id: "pref-002", category: "language", value: "English", updatedAt: datetime() });
CREATE (p3:Preference { id: "pref-003", category: "wake_time",value: "7:00 AM", updatedAt: datetime() });

MATCH (u:User {id:"user-001"}), (p1:Preference {id:"pref-001"}),
      (p2:Preference {id:"pref-002"}), (p3:Preference {id:"pref-003"})
CREATE (u)-[:HAS_PREFERENCE]->(p1)
CREATE (u)-[:HAS_PREFERENCE]->(p2)
CREATE (u)-[:HAS_PREFERENCE]->(p3);

// ── Sample Tasks ──────────────────────────────────────────
CREATE (t1:Task { id:"task-001", title:"Team standup",   status:"pending",   priority:"high",   dueDate:"2025-02-05", createdAt: datetime() });
CREATE (t2:Task { id:"task-002", title:"Buy groceries",  status:"pending",   priority:"medium", dueDate:"2025-02-04", createdAt: datetime() });
CREATE (t3:Task { id:"task-003", title:"Read Neo4j docs", status:"completed", priority:"low",    dueDate:"2025-02-03", createdAt: datetime() });

MATCH (u:User {id:"user-001"}), (t1:Task {id:"task-001"}),
      (t2:Task {id:"task-002"}), (t3:Task {id:"task-003"})
CREATE (u)-[:HAS_TASK]->(t1)
CREATE (u)-[:HAS_TASK]->(t2)
CREATE (u)-[:HAS_TASK]->(t3);

// ── Sample Memory ─────────────────────────────────────────
CREATE (m1:Memory { id:"mem-001", type:"habit",   content:"User usually wakes up at 7 AM",       createdAt: datetime() });
CREATE (m2:Memory { id:"mem-002", type:"fact",    content:"User prefers dark mode interfaces",   createdAt: datetime() });
CREATE (m3:Memory { id:"mem-003", type:"context", content:"User is studying Neo4j graph databases", createdAt: datetime() });

MATCH (u:User {id:"user-001"}), (m1:Memory {id:"mem-001"}),
      (m2:Memory {id:"mem-002"}), (m3:Memory {id:"mem-003"})
CREATE (u)-[:REMEMBERS]->(m1)
CREATE (u)-[:REMEMBERS]->(m2)
CREATE (u)-[:REMEMBERS]->(m3);

// ── Sample Conversation ───────────────────────────────────
CREATE (c1:Conversation {
  id: "conv-001",
  userMessage: "Remind me about the standup tomorrow",
  botReply: "Got it! I've noted your standup reminder.",
  timestamp: datetime()
});

MATCH (u:User {id:"user-001"}), (c1:Conversation {id:"conv-001"})
CREATE (u)-[:HAD_CONVERSATION]->(c1);