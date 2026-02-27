"""Neo4j graph database client utilities."""
from typing import List, Dict, Optional
from app.extensions import neo4j_driver
import structlog

logger = structlog.get_logger()


class Neo4jClient:
    """Client for Neo4j graph database operations."""
    
    @staticmethod
    def create_skill_node(skill_id: str, name: str, category: str = 'other'):
        """Create a Skill node in Neo4j."""
        query = """
        MERGE (s:Skill {id: $skill_id})
        SET s.name = $name,
            s.category = $category,
            s.normalized_name = toLower($name)
        RETURN s
        """
        
        with neo4j_driver.session() as session:
            result = session.run(query, skill_id=skill_id, name=name, category=category)
            return result.single()
    
    @staticmethod
    def create_job_node(job_id: str, title: str, required_skills: List[str] = None):
        """Create a Job node and relationships to skills."""
        query = """
        MERGE (j:Job {id: $job_id})
        SET j.title = $title
        WITH j
        UNWIND $required_skills as skill_name
        MATCH (s:Skill)
        WHERE s.normalized_name = toLower(skill_name) OR s.name = skill_name
        MERGE (j)-[:REQUIRES]->(s)
        RETURN j
        """
        
        with neo4j_driver.session() as session:
            result = session.run(
                query,
                job_id=job_id,
                title=title,
                required_skills=required_skills or []
            )
            return result.single()
    
    @staticmethod
    def create_user_skills(user_id: str, skills: List[Dict]):
        """Create relationships between user and their skills."""
        query = """
        UNWIND $skills as skill
        MATCH (s:Skill {id: skill.skill_id})
        MERGE (u:User {id: $user_id})
        MERGE (u)-[r:HAS_SKILL]->(s)
        SET r.proficiency = skill.proficiency,
            r.source = skill.source
        """
        
        with neo4j_driver.session() as session:
            session.run(query, user_id=user_id, skills=skills)
    
    @staticmethod
    def find_skill_gaps(user_id: str, job_id: str) -> List[Dict]:
        """
        Find skills required by a job that the user doesn't have.
        
        Returns:
            List of missing skills with importance
        """
        query = """
        MATCH (j:Job {id: $job_id})-[:REQUIRES]->(s:Skill)
        WHERE NOT EXISTS {
            MATCH (u:User {id: $user_id})-[:HAS_SKILL]->(s)
        }
        RETURN s.id as skill_id, s.name as name, s.category as category
        """
        
        with neo4j_driver.session() as session:
            result = session.run(query, user_id=user_id, job_id=job_id)
            return [dict(record) for record in result]
    
    @staticmethod
    def find_related_skills(skill_id: str, limit: int = 5) -> List[Dict]:
        """
        Find skills related to a given skill through job requirements.
        
        Returns:
            List of related skills with similarity scores
        """
        query = """
        MATCH (s1:Skill {id: $skill_id})<-[:REQUIRES]-(j:Job)-[:REQUIRES]->(s2:Skill)
        WHERE s1 <> s2
        WITH s2, count(j) as frequency
        ORDER BY frequency DESC
        LIMIT $limit
        RETURN s2.id as skill_id, s2.name as name, s2.category as category, frequency
        """
        
        with neo4j_driver.session() as session:
            result = session.run(query, skill_id=skill_id, limit=limit)
            return [dict(record) for record in result]
    
    @staticmethod
    def find_career_paths(target_skill_id: str, max_depth: int = 3) -> List[List[Dict]]:
        """
        Find learning paths to acquire a target skill.
        
        Returns:
            List of paths (each path is a list of skills)
        """
        query = """
        MATCH path = shortestPath(
            (start:Skill)-[:RELATED_TO*1..%d]->(target:Skill {id: $target_skill_id})
        )
        WITH path, length(path) as path_length
        ORDER BY path_length
        LIMIT 5
        RETURN [node in nodes(path) | {id: node.id, name: node.name, category: node.category}] as path_nodes
        """ % max_depth
        
        with neo4j_driver.session() as session:
            result = session.run(query, target_skill_id=target_skill_id)
            return [record['path_nodes'] for record in result]
    
    @staticmethod
    def create_skill_relationships():
        """
        Create RELATED_TO relationships between skills based on co-occurrence in jobs.
        """
        query = """
        MATCH (s1:Skill)<-[:REQUIRES]-(j:Job)-[:REQUIRES]->(s2:Skill)
        WHERE s1 <> s2
        WITH s1, s2, count(j) as weight
        WHERE weight >= 2
        MERGE (s1)-[r:RELATED_TO]->(s2)
        SET r.weight = weight
        """
        
        with neo4j_driver.session() as session:
            session.run(query)
            logger.info("Created skill relationships based on job co-occurrence")
    
    @staticmethod
    def get_skill_statistics(skill_id: str) -> Dict:
        """Get statistics about a skill (jobs requiring it, related skills, etc.)."""
        query = """
        MATCH (s:Skill {id: $skill_id})
        OPTIONAL MATCH (j:Job)-[:REQUIRES]->(s)
        OPTIONAL MATCH (u:User)-[:HAS_SKILL]->(s)
        WITH s, count(DISTINCT j) as job_count, count(DISTINCT u) as user_count
        RETURN {
            skill_id: s.id,
            name: s.name,
            category: s.category,
            job_count: job_count,
            user_count: user_count
        } as stats
        """
        
        with neo4j_driver.session() as session:
            result = session.run(query, skill_id=skill_id)
            record = result.single()
            return dict(record['stats']) if record else {}


# Global instance
neo4j_client = Neo4jClient()
