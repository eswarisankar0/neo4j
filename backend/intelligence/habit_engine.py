from datetime import datetime
from db.connection import db

class HabitEngine:

    def record_action(self, user_id: str, action_type: str, context: str):
        db.query("""
            MERGE (u:User {user_id: $user_id})
            MERGE (a:ActionLog {type: $action_type, context: $context})
            MERGE (u)-[r:PERFORMED]->(a)
            ON CREATE SET r.count = 1, r.first_seen = $now
            ON MATCH  SET r.count = r.count + 1, r.last_seen = $now
        """, {
            "user_id": user_id,
            "action_type": action_type,
            "context": context,
            "now": datetime.utcnow().isoformat()
        })
        self._promote_to_habit(user_id, action_type, context)

    def _promote_to_habit(self, user_id, action_type, context, threshold=3):
        db.query("""
            MATCH (u:User {user_id: $user_id})-[r:PERFORMED]->
                  (a:ActionLog {type: $action_type, context: $context})
            WHERE r.count >= $threshold
            MERGE (h:Habit {
                user_id: $user_id,
                action_type: $action_type,
                context: $context
            })
            ON CREATE SET h.frequency = r.count, h.confidence = 0.6
            ON MATCH  SET h.frequency = r.count,
                          h.confidence = CASE
                              WHEN h.confidence < 0.95
                              THEN h.confidence + 0.05
                              ELSE 0.95 END
            MERGE (u)-[:EXHIBITS_HABIT]->(h)
        """, {
            "user_id": user_id,
            "action_type": action_type,
            "context": context,
            "threshold": threshold
        })

    def get_habits(self, user_id: str, min_confidence: float = 0.6):
        return db.query("""
            MATCH (u:User {user_id: $user_id})-[:EXHIBITS_HABIT]->(h:Habit)
            WHERE h.confidence >= $min_confidence
            RETURN h ORDER BY h.confidence DESC
        """, {"user_id": user_id, "min_confidence": min_confidence})