def initialize_schema(db):
    statements = [
        "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.user_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Memory) REQUIRE m.memory_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Action) REQUIRE a.action_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE",
        "CREATE INDEX IF NOT EXISTS FOR (m:Memory) ON (m.created_at)",
        "CREATE INDEX IF NOT EXISTS FOR (m:Memory) ON (m.context_type)",
        "CREATE INDEX IF NOT EXISTS FOR (h:Habit) ON (h.frequency)",
    ]
    for stmt in statements:
        db.query(stmt)
    print(" Schema initialized successfully")