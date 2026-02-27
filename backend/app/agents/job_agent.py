"""Job Intelligence Agent."""
from typing import Dict, List, Optional
from datetime import datetime
import structlog

import app.extensions as extensions  # ✅ FIXED
from app.extensions import db
from app.models.job import Job, Company
from app.utils.skill_extractor import extract_skills_from_text
from app.utils.ml_models import get_sentence_transformer

logger = structlog.get_logger()


class JobAgent:
    """
    Job Intelligence Agent responsible for:
    - Scraping job data from multiple sources
    - Cleaning and structuring job descriptions
    - Generating embeddings
    - Storing metadata in PostgreSQL
    - Storing embeddings in Qdrant
    - Storing keywords in Elasticsearch
    """

    def __init__(self):
        self.model = get_sentence_transformer()

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------

    def process_job_description(self, description: str, requirements: str = None, responsibilities: str = None) -> Dict:
        """
        Process job description and extract skills from all available text.
        
        Args:
            description: Main job description
            requirements: Job requirements text
            responsibilities: Job responsibilities text
            
        Returns:
            Dict with cleaned description and extracted skills
        """
        # Combine all text for skill extraction
        combined_text = description or ""
        if requirements:
            combined_text += " " + requirements
        if responsibilities:
            combined_text += " " + responsibilities
        
        cleaned_text = self._clean_text(description or "")
        cleaned_combined = self._clean_text(combined_text)
        
        # Extract skills from combined text for better coverage
        skills = extract_skills_from_text(cleaned_combined)
        
        # Also extract tech keywords that might not be in our skill taxonomy
        additional_skills = self._extract_additional_tech_keywords(cleaned_combined)
        
        # Merge skills, avoiding duplicates
        existing_names = {s["normalized_name"] for s in skills}
        for skill_name in additional_skills:
            if skill_name.lower() not in existing_names:
                skills.append({
                    "name": skill_name,
                    "normalized_name": skill_name.lower(),
                    "category": "technical",
                    "mentions": 1,
                    "confidence": 0.7
                })
        
        return {
            "cleaned_description": cleaned_text,
            "extracted_skills": skills,
            "skill_names": [s["name"] for s in skills],
        }
    
    def _extract_additional_tech_keywords(self, text: str) -> List[str]:
        """
        Extract additional tech keywords that might not be in the main skill taxonomy.
        This helps catch skills mentioned in job titles and requirements.
        """
        if not text:
            return []
        
        import re
        text_lower = text.lower()
        
        # Extended tech keywords list
        tech_keywords = {
            'python', 'javascript', 'typescript', 'java', 'c++', 'c#', 'go', 'golang', 'rust',
            'ruby', 'php', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash',
            'sql', 'html', 'css', 'sass', 'less', 'dart', 'julia', 'groovy', 'lua',
            'react', 'reactjs', 'vue', 'vuejs', 'angular', 'svelte', 'nextjs', 'next.js', 
            'nuxt', 'django', 'flask', 'fastapi', 'spring', 'spring boot', 'laravel', 
            'express', 'expressjs', 'nestjs', 'nest.js', 'rails', 'aspnet', 'bootstrap',
            'tailwind', 'material-ui', 'mui', 'antd', 'jquery',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'pandas', 'numpy',
            'postgresql', 'postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch', 
            'cassandra', 'dynamodb', 'sqlite', 'oracle', 'sql server', 'mssql', 'firebase',
            'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'docker', 'kubernetes', 
            'k8s', 'terraform', 'ansible', 'jenkins', 'github actions', 'gitlab ci',
            'git', 'github', 'gitlab', 'bitbucket', 'jira', 'confluence', 'slack', 
            'postman', 'swagger', 'graphql', 'rest api', 'restful',
            'tableau', 'powerbi', 'power bi', 'snowflake', 'bigquery', 'spark', 'hadoop',
            'react native', 'flutter', 'ios', 'android', 'xamarin', 'ionic',
            'jest', 'mocha', 'cypress', 'selenium', 'playwright', 'junit', 'pytest',
            'machine learning', 'deep learning', 'ai', 'artificial intelligence',
            'data science', 'data engineering', 'nlp', 'computer vision',
            'blockchain', 'web3', 'devops', 'microservices', 'serverless', 'ci/cd',
            'agile', 'scrum', 'kanban', 'oop', 'system design', 'api design',
            'frontend', 'backend', 'fullstack', 'full stack', 'web development',
        }
        
        found = []
        for keyword in tech_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                found.append(keyword)
        
        return found

    def _clean_text(self, text: str) -> str:
        import re

        text = " ".join(text.split())
        text = re.sub(r"[^\w\s.,;:!?()-]", " ", text)
        return text.strip()

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        if not self.model:
            raise RuntimeError("Model not loaded")

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def store_job_embedding(self, job_id: str, embedding: List[float]):
        try:
            from qdrant_client.models import PointStruct

            point = PointStruct(
                id=job_id,
                vector=embedding,
                payload={"job_id": job_id, "type": "job"},
            )

            # ✅ FIXED: use live extensions reference
            extensions.qdrant_client.upsert(
                collection_name="job_embeddings",
                points=[point],
            )

            logger.info(f"Stored embedding for job: {job_id}")

        except Exception as e:
            logger.error(f"Failed to store job embedding: {e}")
            raise

    # ------------------------------------------------------------------
    # Elasticsearch
    # ------------------------------------------------------------------

    def index_job_in_elasticsearch(self, job: Job):
        try:
            document = {
                "title": job.title,
                "description": job.description,
                "skills": job.required_skills or [],
                "company": job.company.name if job.company else "",
                "location": job.location or "",
                "created_at": job.created_at.isoformat()
                if job.created_at
                else None,
            }

            # ✅ FIXED
            extensions.es_client.index(
                index="jobs",
                id=job.id,
                document=document,
            )

            logger.info(f"Indexed job in Elasticsearch: {job.id}")

        except Exception as e:
            logger.error(f"Failed to index job in Elasticsearch: {e}")
            raise

    # ------------------------------------------------------------------
    # Company Handling
    # ------------------------------------------------------------------

    def create_or_update_company(self, company_data: Dict) -> Company:
        name = company_data.get("name", "")
        if not name:
            raise ValueError("Company name is required")

        company = Company.query.filter_by(name=name).first()

        if company:
            company.description = company_data.get("description", company.description)
            company.industry = company_data.get("industry", company.industry)
            company.website = company_data.get("website", company.website)
            company.location = company_data.get("location", company.location)
        else:
            company = Company(
                name=name,
                description=company_data.get("description", ""),
                industry=company_data.get("industry", ""),
                website=company_data.get("website", ""),
                location=company_data.get("location", ""),
            )
            db.session.add(company)

        db.session.commit()
        return company

    # ------------------------------------------------------------------
    # Job Creation
    # ------------------------------------------------------------------

    def create_job(self, job_data: Dict) -> Job:
        # Process job description with all available text for better skill extraction
        processed = self.process_job_description(
            description=job_data.get("description", ""),
            requirements=job_data.get("requirements", ""),
            responsibilities=job_data.get("responsibilities", "")
        )

        company = None
        if job_data.get("company"):
            company = self.create_or_update_company(job_data["company"])

        job = Job(
            title=job_data.get("title", ""),
            company_id=company.id if company else None,
            description=processed["cleaned_description"],
            requirements=job_data.get("requirements", ""),
            responsibilities=job_data.get("responsibilities", ""),
            location=job_data.get("location", ""),
            is_remote=job_data.get("is_remote", False),
            is_hybrid=job_data.get("is_hybrid", False),
            salary_min=job_data.get("salary_min"),
            salary_max=job_data.get("salary_max"),
            salary_currency=job_data.get("salary_currency", "USD"),
            employment_type=job_data.get("employment_type", "full-time"),
            experience_level=job_data.get("experience_level"),
            source_url=job_data.get("source_url", ""),
            source_platform=job_data.get("source_platform", "manual"),
            external_id=job_data.get("external_id", ""),
            required_skills=processed["skill_names"],
            is_active=True,
        )

        if job_data.get("posted_at"):
            try:
                job.posted_at = datetime.fromisoformat(
                    job_data["posted_at"].replace("Z", "+00:00")
                )
            except Exception:
                pass

        db.session.add(job)
        db.session.commit()

        # Build comprehensive embedding text from all job fields
        embedding_parts = [
            job.title,
            processed['cleaned_description'],
        ]
        
        # Add requirements and responsibilities if available
        if job.requirements:
            embedding_parts.append(job.requirements)
        if job.responsibilities:
            embedding_parts.append(job.responsibilities)
        
        # Add skills with higher weight (repeat them)
        if processed['skill_names']:
            embedding_parts.extend(processed['skill_names'] * 2)  # Double weight for skills
        
        embedding_text = " ".join(embedding_parts)

        embedding = self.generate_embedding(embedding_text)
        self.store_job_embedding(job.id, embedding)

        self.index_job_in_elasticsearch(job)

        logger.info(f"Created job: {job.id}")
        return job

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_jobs_by_vector(
        self, query_vector: List[float], limit: int = 10
    ) -> List[Dict]:

        try:
            from qdrant_client.models import SearchParams

            results = extensions.qdrant_client.query_points(
                collection_name="job_embeddings",
                query=query_vector,
                limit=limit,
                search_params=SearchParams(hnsw_ef=128, exact=False),
            )

            jobs = []
            for point in results.points:
                job = Job.query.get(point.id)
                if job and job.is_active:
                    jobs.append(
                        {"job": job.to_dict(), "score": point.score}
                    )

            return jobs

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def search_jobs_by_keywords(
        self, query: str, filters: Optional[Dict] = None
    ) -> List[Dict]:

        try:
            search_body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^3",
                            "description",
                            "skills^2",
                            "company",
                            "location",
                        ],
                        "type": "best_fields",
                    }
                }
            }

            if filters:
                must_clauses = []
                for key, value in filters.items():
                    must_clauses.append({"term": {key: value}})

                if must_clauses:
                    search_body["query"] = {
                        "bool": {
                            "must": [
                                search_body["query"],
                                *must_clauses,
                            ]
                        }
                    }

            response = extensions.es_client.search(
                index="jobs", body=search_body
            )

            jobs = []
            for hit in response["hits"]["hits"]:
                job = Job.query.get(hit["_id"])
                if job and job.is_active:
                    jobs.append(
                        {"job": job.to_dict(), "score": hit["_score"]}
                    )

            return jobs

        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------

_job_agent = None


def get_job_agent() -> JobAgent:
    global _job_agent
    if _job_agent is None:
        _job_agent = JobAgent()
    return _job_agent