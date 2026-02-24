from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv()

class Neo4jConnection:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(
                os.getenv("NEO4J_USER", "neo4j"),
                os.getenv("NEO4J_PASSWORD")
            )
        )
        print("✅ Connected to Neo4j")

    def query(self, cypher, parameters=None):
        with self.driver.session() as session:
            return session.run(cypher, parameters or {}).data()

    def close(self):
        self.driver.close()

db = Neo4jConnection()