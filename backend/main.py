from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.connection import db
from db.schema import initialize_schema
from memory.memory_engine import MemoryEngine
from intelligence.habit_engine import HabitEngine
from intelligence.intent_processor import IntentProcessor
from pydantic import BaseModel
import anthropic
import os

app = FastAPI(title="Context-Aware AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_engine    = MemoryEngine()
habit_engine     = HabitEngine()
intent_processor = IntentProcessor()

# ── Claude Client ────────────────────────────────
claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Pydantic Models ──────────────────────────────
class MemoryRequest(BaseModel):
    user_id: str
    content: str
    context_type: str
    entities: list = []
    embedding: list = []

class IntentRequest(BaseModel):
    user_id: str
    raw_input: str
    intent_type: str
    confidence: float = 1.0
    triggered_memory_id: str = None

class ActionRequest(BaseModel):
    intent_id: str
    action_type: str
    payload: dict
    status: str = "success"

class ChatRequest(BaseModel):
    user_id: str
    message: str

# ── Startup ──────────────────────────────────────
@app.on_event("startup")
def startup():
    initialize_schema(db)
    print("🚀 Assistant backend is live!")

# ── Routes ───────────────────────────────────────
@app.get("/")
def root():
    return {"status": "running", "message": "AI Assistant API is live ✅"}

# 🤖 MAIN CHAT ENDPOINT — uses Claude API
@app.post("/chat")
def chat(req: ChatRequest):
    # 1. Fetch user profile from dataset
    user_profile = db.query("""
        MATCH (u:User {user_id: $user_id})
        RETURN u.name AS name, u.age AS age, u.city AS city
    """, {"user_id": req.user_id})
    profile_text = f"Name: {user_profile[0]['name']}, Age: {user_profile[0]['age']}, City: {user_profile[0]['city']}" \
        if user_profile else "Unknown user"

    # 2. Fetch user's past memories
    memories = memory_engine.recall_memories(req.user_id, limit=5)
    memory_text = "\n".join(
        [f"- {m['m']['content']}" for m in memories]
    ) if memories else "No previous memories."

    # 3. Fetch user's habits
    habits = habit_engine.get_habits(req.user_id)
    habit_text = "\n".join(
        [f"- {h['h']['action_type']}: {h['h']['context']}" for h in habits]
    ) if habits else "No habits detected yet."

    # 4. Fetch user's tasks from dataset
    tasks = db.query("""
        MATCH (u:User {user_id: $user_id})-[:CREATED]->(t:Task)
        RETURN t.title AS title, t.priority AS priority, t.status AS status
        LIMIT 5
    """, {"user_id": req.user_id})
    task_text = "\n".join(
        [f"- {t['title']} ({t['priority']} priority, {t['status']})"
         for t in tasks]
    ) if tasks else "No tasks found."

    # 5. Fetch user's reminders from dataset
    reminders = db.query("""
        MATCH (u:User {user_id: $user_id})-[:SET]->(r:Reminder)
        RETURN r.text AS text, r.scheduledTime AS scheduledTime
        LIMIT 5
    """, {"user_id": req.user_id})
    reminder_text = "\n".join(
        [f"- {r['text']} at {r['scheduledTime']}"
         for r in reminders]
    ) if reminders else "No reminders found."

    # 6. Fetch user's events from dataset
    events = db.query("""
        MATCH (u:User {user_id: $user_id})-[:ATTENDS]->(e:Event)
        RETURN e.title AS title, e.location AS location, e.startTime AS startTime
        LIMIT 5
    """, {"user_id": req.user_id})
    event_text = "\n".join(
        [f"- {e['title']} at {e['location']} on {e['startTime']}"
         for e in events]
    ) if events else "No events found."

    # 7. Build system prompt with full user context
    system_prompt = f"""You are a personal AI assistant with persistent memory.
You know this user personally and remember everything about them.

User Profile:
{profile_text}

User's recent memories:
{memory_text}

User's detected habits:
{habit_text}

User's tasks:
{task_text}

User's upcoming reminders:
{reminder_text}

User's events:
{event_text}

Use all this context to give personalized, helpful responses.
Address the user by their name. Keep responses concise and natural."""

    # 8. Call Claude API
    response = claude.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": req.message}
        ]
    )

    reply = response.content[0].text

    # 9. Store this conversation as a memory
    memory_engine.store_memory(
        user_id=req.user_id,
        content=f"User said: {req.message} | Assistant replied: {reply}",
        context_type="conversation",
        entities=[]
    )

    # 10. Log the intent
    intent_processor.log_intent(
        user_id=req.user_id,
        raw_input=req.message,
        intent_type="conversation",
        confidence=1.0
    )

    return {"reply": reply, "status": "success"}

# ── Memory Routes ────────────────────────────────
@app.post("/memory/store")
def store_memory(req: MemoryRequest):
    memory_id = memory_engine.store_memory(
        req.user_id, req.content, req.context_type,
        req.entities, req.embedding
    )
    return {"memory_id": memory_id, "status": "stored"}

@app.get("/memory/recall/{user_id}")
def recall_memory(user_id: str, context_type: str = None, entity: str = None):
    memories = memory_engine.recall_memories(user_id, context_type, entity)
    return {"memories": memories}

@app.delete("/memory/{memory_id}")
def delete_memory(memory_id: str):
    memory_engine.delete_memory(memory_id)
    return {"status": "deleted"}

# ── Intent Routes ────────────────────────────────
@app.post("/intent/log")
def log_intent(req: IntentRequest):
    intent_id = intent_processor.log_intent(
        req.user_id, req.raw_input, req.intent_type,
        req.confidence, req.triggered_memory_id
    )
    habit_engine.record_action(req.user_id, req.intent_type, req.raw_input)
    return {"intent_id": intent_id}

# ── Action Routes ────────────────────────────────
@app.post("/action/log")
def log_action(req: ActionRequest):
    action_id = intent_processor.log_action(
        req.intent_id, req.action_type, req.payload, req.status
    )
    return {"action_id": action_id}

# ── Habit Routes ─────────────────────────────────
@app.get("/habits/{user_id}")
def get_habits(user_id: str, min_confidence: float = 0.6):
    habits = habit_engine.get_habits(user_id, min_confidence)
    return {"habits": habits}

# ── Full Context Route ───────────────────────────
@app.get("/user/{user_id}/context")
def get_full_context(user_id: str):
    result = db.query("""
        MATCH (u:User {user_id: $user_id})
        OPTIONAL MATCH (u)-[:HAS_MEMORY]->(m:Memory)
        OPTIONAL MATCH (u)-[:EXHIBITS_HABIT]->(h:Habit)
        OPTIONAL MATCH (u)-[:CREATED]->(t:Task)
        OPTIONAL MATCH (u)-[:ATTENDS]->(e:Event)
        OPTIONAL MATCH (u)-[:SET]->(r:Reminder)
        RETURN
            collect(DISTINCT m)[..5] AS recent_memories,
            collect(DISTINCT h)      AS habits,
            collect(DISTINCT t)[..5] AS recent_tasks,
            collect(DISTINCT e)[..5] AS recent_events,
            collect(DISTINCT r)[..5] AS recent_reminders
    """, {"user_id": user_id})
    return result[0] if result else {}