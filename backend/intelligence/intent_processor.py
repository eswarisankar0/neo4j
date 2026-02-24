import uuid
from datetime import datetime
from db.connection import db

class IntentProcessor:

    def log_intent(self, user_id: str, raw_input: str,
                   intent_type: str, confidence: float,
                   memory_id: str = None):
        intent_id = str(uuid.uuid4())

        db.query("""
            MERGE (u:User {user_id: $user_id})
            CREATE (i:Intent {
                intent_id: $intent_id,
                raw_input: $raw_input,
                intent_type: $intent_type,
                confidence: $confidence,
                created_at: $now
            })
            CREATE (u)-[:ISSUED]->(i)
        """, {
            "user_id": user_id,
            "intent_id": intent_id,
            "raw_input": raw_input,
            "intent_type": intent_type,
            "confidence": confidence,
            "now": datetime.utcnow().isoformat()
        })

        if memory_id:
            db.query("""
                MATCH (m:Memory {memory_id: $memory_id})
                MATCH (i:Intent {intent_id: $intent_id})
                MERGE (m)-[:TRIGGERED_INTENT]->(i)
            """, {"memory_id": memory_id, "intent_id": intent_id})

        return intent_id

    def log_action(self, intent_id: str, action_type: str,
                   payload: dict, status: str = "success"):
        action_id = str(uuid.uuid4())

        db.query("""
            MATCH (i:Intent {intent_id: $intent_id})
            CREATE (a:Action {
                action_id: $action_id,
                action_type: $action_type,
                payload: $payload,
                status: $status,
                executed_at: $now
            })
            CREATE (i)-[:RESULTED_IN]->(a)
        """, {
            "intent_id": intent_id,
            "action_id": action_id,
            "action_type": action_type,
            "payload": str(payload),
            "status": status,
            "now": datetime.utcnow().isoformat()
        })

        return action_id