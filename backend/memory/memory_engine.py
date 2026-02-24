import uuid
from datetime import datetime
from db.connection import db

class MemoryEngine:

    def store_memory(self, user_id: str, content: str,
                     context_type: str, entities: list, embedding: list = []):
        memory_id = str(uuid.uuid4())

        db.query("MERGE (u:User {user_id: $user_id})", {"user_id": user_id})

        db.query("""
            CREATE (m:Memory {
                memory_id: $memory_id,
                content: $content,
                context_type: $context_type,
                embedding: $embedding,
                created_at: $created_at,
                access_count: 0,
                last_accessed: $created_at
            })
        """, {
            "memory_id": memory_id,
            "content": content,
            "context_type": context_type,
            "embedding": embedding,
            "created_at": datetime.utcnow().isoformat()
        })

        db.query("""
            MATCH (u:User {user_id: $user_id})
            MATCH (m:Memory {memory_id: $memory_id})
            CREATE (u)-[:HAS_MEMORY {strength: 1.0}]->(m)
        """, {"user_id": user_id, "memory_id": memory_id})

        for entity_name in entities:
            db.query("""
                MERGE (e:Entity {name: $name})
                WITH e
                MATCH (m:Memory {memory_id: $memory_id})
                MERGE (m)-[:REFERENCES]->(e)
            """, {"name": entity_name, "memory_id": memory_id})

        print(f"✅ Memory stored: {memory_id}")
        return memory_id

    def recall_memories(self, user_id: str, context_type: str = None,
                        entity: str = None, limit: int = 10):

        if entity:
            return db.query("""
                MATCH (u:User {user_id: $user_id})-[:HAS_MEMORY]->(m:Memory)
                      -[:REFERENCES]->(e:Entity {name: $entity})
                RETURN m ORDER BY m.created_at DESC LIMIT $limit
            """, {"user_id": user_id, "entity": entity, "limit": limit})

        if context_type:
            return db.query("""
                MATCH (u:User {user_id: $user_id})-[:HAS_MEMORY]->(m:Memory)
                WHERE m.context_type = $context_type
                RETURN m ORDER BY m.created_at DESC LIMIT $limit
            """, {"user_id": user_id, "context_type": context_type, "limit": limit})

        return db.query("""
            MATCH (u:User {user_id: $user_id})-[:HAS_MEMORY]->(m:Memory)
            RETURN m ORDER BY m.created_at DESC LIMIT $limit
        """, {"user_id": user_id, "limit": limit})

    def delete_memory(self, memory_id: str):
        db.query("""
            MATCH (m:Memory {memory_id: $memory_id})
            DETACH DELETE m
        """, {"memory_id": memory_id})
        print(f"🗑️ Memory deleted: {memory_id}")