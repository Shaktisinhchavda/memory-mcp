"""
Neo4j Graph Store — Manages the knowledge graph in Neo4j.

Handles:
- Connection to local Neo4j instance
- Creating/merging entity nodes
- Creating relationships between entities
- Graph search queries (find connected context)
- Statistics and schema info
"""

import logging
import os
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)

# Read Neo4j connection settings from environment (or .env via settings)
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "neo4j")


class GraphStore:
    """
    Neo4j-backed knowledge graph store.

    Stores entities as nodes and relationships as edges.
    Node labels match entity types: Person, Technology, Topic, Project, Task, Document.
    """

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
    ):
        self._uri = uri
        self._auth = (user, password)
        self._driver = None

    def _get_driver(self):
        """Lazy-init the Neo4j driver."""
        if self._driver is None:
            self._driver = GraphDatabase.driver(self._uri, auth=self._auth)
        return self._driver

    def is_connected(self) -> bool:
        """Check if Neo4j is reachable."""
        try:
            driver = self._get_driver()
            driver.verify_connectivity()
            return True
        except (ServiceUnavailable, AuthError, Exception) as e:
            logger.warning(f"Neo4j not available: {e}")
            return False

    def close(self):
        """Close the driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    # ── Node Operations ──

    def merge_entity(self, name: str, entity_type: str, properties: dict | None = None) -> None:
        """
        Create or update an entity node.

        Uses MERGE to avoid duplicates. The label is derived from entity_type.

        Args:
            name: Entity name (used as unique key).
            entity_type: One of person, technology, topic, project, task, document.
            properties: Additional properties to set on the node.
        """
        label = entity_type.capitalize()
        props = {**(properties or {}), "name": name, "entity_type": entity_type}
        prop_str = ", ".join(f"n.{k} = ${k}" for k in props if k != "name")

        query = f"MERGE (n:{label} {{name: $name}}) SET {prop_str}" if prop_str else f"MERGE (n:{label} {{name: $name}})"

        driver = self._get_driver()
        driver.execute_query(query, **props, database_="neo4j")

    def merge_relationship(
        self,
        from_name: str,
        from_type: str,
        to_name: str,
        to_type: str,
        rel_type: str,
        properties: dict | None = None,
    ) -> None:
        """
        Create or update a relationship between two entities.

        Ensures both nodes exist (MERGE) before creating the relationship.

        Args:
            from_name: Source entity name.
            from_type: Source entity type.
            to_name: Target entity name.
            to_type: Target entity type.
            rel_type: Relationship type (e.g., RELATED_TO, MENTIONED_IN, USES).
            properties: Additional relationship properties.
        """
        from_label = from_type.capitalize()
        to_label = to_type.capitalize()

        query = f"""
        MERGE (a:{from_label} {{name: $from_name}})
        MERGE (b:{to_label} {{name: $to_name}})
        MERGE (a)-[r:{rel_type}]->(b)
        """

        if properties:
            prop_sets = ", ".join(f"r.{k} = ${k}" for k in properties)
            query += f" SET {prop_sets}"

        driver = self._get_driver()
        params = {"from_name": from_name, "to_name": to_name, **(properties or {})}
        driver.execute_query(query, **params, database_="neo4j")

    # ── Bulk Operations ──

    def ingest_extraction(self, extraction: dict[str, Any]) -> dict[str, int]:
        """
        Ingest entities and relationships from an extraction result.

        Args:
            extraction: Output from extractor.extract_from_file().

        Returns:
            Dict with counts of nodes and relationships created.
        """
        if "error" in extraction:
            return {"error": extraction["error"]}

        nodes_created = 0
        rels_created = 0

        # Create entity nodes
        for entity in extraction.get("entities", []):
            self.merge_entity(
                name=entity["name"],
                entity_type=entity["type"],
                properties={"source": entity.get("source", "")},
            )
            nodes_created += 1

        # Create document node for source file
        source_file = extraction.get("file", "")
        if source_file:
            self.merge_entity(source_file, "document", {"file_path": source_file})

        # Create relationships
        for rel in extraction.get("relationships", []):
            self.merge_relationship(
                from_name=rel["from_name"],
                from_type=rel["from_type"],
                to_name=rel["to_name"],
                to_type=rel["to_type"],
                rel_type=rel["rel_type"],
            )
            rels_created += 1

        return {"nodes_created": nodes_created, "relationships_created": rels_created}

    # ── Query Operations ──

    def graph_search(self, entity_name: str, max_depth: int = 2) -> dict[str, Any]:
        """
        Search the graph for an entity and its connected context.

        Returns the entity, its direct connections, and connections
        up to max_depth hops away.

        Args:
            entity_name: Name of the entity to search for.
            max_depth: How many hops to traverse (default 2).

        Returns:
            Dict with the entity, connected nodes, and relationships.
        """
        max_depth = min(max(1, max_depth), 4)

        query = """
        MATCH (start)
        WHERE toLower(start.name) CONTAINS toLower($name)
        OPTIONAL MATCH path = (start)-[*1..""" + str(max_depth) + """]-(connected)
        WITH start, collect(DISTINCT {
            name: connected.name,
            type: labels(connected)[0],
            entity_type: connected.entity_type
        }) AS connections,
        collect(DISTINCT type(last(relationships(path)))) AS rel_types
        RETURN start.name AS entity_name,
               labels(start)[0] AS entity_type,
               start.entity_type AS sub_type,
               connections,
               rel_types
        LIMIT 10
        """

        driver = self._get_driver()
        records, _, _ = driver.execute_query(query, name=entity_name, database_="neo4j")

        results = []
        for record in records:
            connections = [c for c in record["connections"] if c["name"] is not None]
            results.append({
                "entity": record["entity_name"],
                "type": record["entity_type"],
                "connections": connections,
                "relationship_types": [r for r in record["rel_types"] if r],
            })

        return {
            "query": entity_name,
            "results_count": len(results),
            "results": results,
        }

    def find_paths(self, from_entity: str, to_entity: str) -> list[dict[str, Any]]:
        """
        Find paths between two entities in the graph.

        Args:
            from_entity: Starting entity name.
            to_entity: Target entity name.

        Returns:
            List of paths with nodes and relationships.
        """
        query = """
        MATCH (a), (b)
        WHERE toLower(a.name) CONTAINS toLower($from_name)
          AND toLower(b.name) CONTAINS toLower($to_name)
        MATCH path = shortestPath((a)-[*..5]-(b))
        RETURN [node IN nodes(path) | {name: node.name, type: labels(node)[0]}] AS nodes,
               [rel IN relationships(path) | type(rel)] AS relationships
        LIMIT 5
        """

        driver = self._get_driver()
        records, _, _ = driver.execute_query(
            query, from_name=from_entity, to_name=to_entity, database_="neo4j"
        )

        return [{"nodes": r["nodes"], "relationships": r["relationships"]} for r in records]

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
        driver = self._get_driver()

        # Node count by label
        records, _, _ = driver.execute_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC",
            database_="neo4j",
        )
        node_counts = {r["label"]: r["count"] for r in records}

        # Relationship count
        records2, _, _ = driver.execute_query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count ORDER BY count DESC",
            database_="neo4j",
        )
        rel_counts = {r["type"]: r["count"] for r in records2}

        total_nodes = sum(node_counts.values())
        total_rels = sum(rel_counts.values())

        return {
            "total_nodes": total_nodes,
            "total_relationships": total_rels,
            "nodes_by_type": node_counts,
            "relationships_by_type": rel_counts,
        }

    def clear_graph(self) -> dict[str, str]:
        """Delete all nodes and relationships. Use with caution!"""
        driver = self._get_driver()
        driver.execute_query("MATCH (n) DETACH DELETE n", database_="neo4j")
        return {"status": "Graph cleared"}
