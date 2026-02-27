"""Recommendation & Career Agent."""
from typing import Dict, List, Optional
import structlog

from app.extensions import qdrant_client
from app.models.user import UserSkill
from app.models.job import Job
from app.models.skill import Skill
from app.utils.neo4j_client import neo4j_client
from app.utils.ml_models import get_sentence_transformer

logger = structlog.get_logger()


class RecommendationAgent:
    """
    Recommendation & Career Agent responsible for:
    - Matching user skills with jobs
    - Performing hybrid ranking (vector + keyword)
    - Detecting skill gaps
    - Generating learning paths using Neo4j
    - Providing explainable recommendations
    """

    def __init__(self):
        self.model = get_sentence_transformer()

    def get_user_profile_vector(self, user_id: str) -> Optional[List[float]]:
        user_skills = UserSkill.query.filter_by(user_id=user_id).all()

        if not user_skills:
            return None

        skill_names = [us.skill.name for us in user_skills if us.skill]

        if not skill_names:
            return None

        skill_text = " ".join(skill_names)
        embedding = self.model.encode(skill_text, convert_to_numpy=True)
        return embedding.tolist()

    # ✅ FIXED FOR QDRANT 1.16.2
    def vector_search_jobs(self, user_id: str, limit: int = 20) -> List[Dict]:
        user_vector = self.get_user_profile_vector(user_id)

        if not user_vector:
            logger.warning(f"No user profile vector for user: {user_id}")
            return []

        try:
            results = qdrant_client.query_points(
                collection_name="job_embeddings",
                query=user_vector,
                limit=limit,
            )

            jobs = []
            for point in results.points:
                job = Job.query.get(point.id)
                if job and job.is_active:
                    jobs.append({
                        "job": job.to_dict(),
                        "vector_score": point.score,
                        "match_type": "vector",
                    })

            return jobs

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def keyword_search_jobs(self, user_id: str, limit: int = 20) -> List[Dict]:
        user_skills = UserSkill.query.filter_by(user_id=user_id).all()
        skill_names = [us.skill.name for us in user_skills if us.skill]

        if not skill_names:
            return []

        query = " OR ".join(skill_names[:10])

        try:
            from app.extensions import es_client

            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "description", "skills^3"],
                        "type": "best_fields",
                        "operator": "or",
                    }
                },
                "size": limit,
            }

            response = es_client.search(index="jobs", body=search_body)

            jobs = []
            for hit in response["hits"]["hits"]:
                job = Job.query.get(hit["_id"])
                if job and job.is_active:
                    jobs.append({
                        "job": job.to_dict(),
                        "keyword_score": hit["_score"],
                        "match_type": "keyword",
                    })

            return jobs

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def hybrid_rank_jobs(self, user_id: str, limit: int = 20) -> List[Dict]:
        vector_results = self.vector_search_jobs(user_id, limit=limit * 2)
        keyword_results = self.keyword_search_jobs(user_id, limit=limit * 2)

        job_scores = {}

        for result in vector_results:
            job_id = result["job"]["id"]
            job_scores[job_id] = {
                "job": result["job"],
                "vector_score": result.get("vector_score", 0),
                "keyword_score": 0,
            }

        for result in keyword_results:
            job_id = result["job"]["id"]
            if job_id in job_scores:
                job_scores[job_id]["keyword_score"] = result.get(
                    "keyword_score", 0
                )
            else:
                job_scores[job_id] = {
                    "job": result["job"],
                    "vector_score": 0,
                    "keyword_score": result.get("keyword_score", 0),
                }

        if not job_scores:
            return []

        max_vector = max(s["vector_score"] for s in job_scores.values())
        max_keyword = max(s["keyword_score"] for s in job_scores.values())

        ranked_jobs = []

        for scores in job_scores.values():
            normalized_vector = (
                scores["vector_score"] / max_vector if max_vector > 0 else 0
            )
            normalized_keyword = (
                scores["keyword_score"] / max_keyword if max_keyword > 0 else 0
            )

            combined_score = (0.6 * normalized_vector) + (0.4 * normalized_keyword)

            ranked_jobs.append({
                "job": scores["job"],
                "match_score": round(combined_score * 100, 2),
                "vector_score": round(normalized_vector * 100, 2),
                "keyword_score": round(normalized_keyword * 100, 2),
            })

        ranked_jobs.sort(key=lambda x: x["match_score"], reverse=True)

        return ranked_jobs[:limit]

    def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict]:
        ranked_jobs = self.hybrid_rank_jobs(user_id, limit=limit)

        recommendations = []
        for item in ranked_jobs:
            recommendations.append({
                "job": item["job"],
                "match_score": item["match_score"],
                "explanation": f"Match score: {item['match_score']}%",
            })

        return recommendations


_recommendation_agent = None


def get_recommendation_agent() -> RecommendationAgent:
    global _recommendation_agent
    if _recommendation_agent is None:
        _recommendation_agent = RecommendationAgent()
    return _recommendation_agent