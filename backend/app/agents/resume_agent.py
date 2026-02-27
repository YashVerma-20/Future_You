"""Resume Intelligence Agent."""
from typing import Dict, List
import structlog
import os
import app.extensions as extensions  # ✅ FIXED
from app.extensions import db
from app.models.resume import Resume
from app.models.skill import Skill
from app.models.user import UserSkill
from app.utils.pdf_parser import extract_text_from_pdf, extract_pdf_metadata
from app.utils.docx_parser import extract_text_from_docx, extract_docx_metadata
from app.utils.skill_extractor import (
    extract_skills_from_text,
    extract_resume_sections,
)
from app.utils.ml_models import get_sentence_transformer

logger = structlog.get_logger()


class ResumeAgent:
    """
    Resume Intelligence Agent responsible for:
    - Parsing resume documents (PDF/DOCX)
    - Extracting skills
    - Normalizing skills
    - Storing structured data in PostgreSQL
    - Storing embeddings in Qdrant
    """

    def __init__(self):
        self.model = get_sentence_transformer()

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_resume(self, file_content: bytes, file_type: str) -> Dict:
        logger.info(f"Parsing resume of type: {file_type}")

        if file_type == "pdf":
            text = extract_text_from_pdf(file_content)
            metadata = extract_pdf_metadata(file_content)
        elif file_type in ["docx", "doc"]:
            text = extract_text_from_docx(file_content)
            metadata = extract_docx_metadata(file_content)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        if not text:
            raise ValueError("Failed to extract text from document")

        return {"text": text, "metadata": metadata}

    # ------------------------------------------------------------------
    # Skill Extraction
    # ------------------------------------------------------------------

    def extract_skills(self, text: str) -> List[Dict]:
        logger.info("Extracting skills from resume")
        return extract_skills_from_text(text)

    def normalize_skills(self, skills: List[Dict]) -> List[Dict]:
        normalized_skills = []

        for skill in skills:
            normalized_name = skill["normalized_name"]

            existing_skill = Skill.find_by_name(normalized_name)

            if existing_skill:
                skill["skill_id"] = existing_skill.id
                skill["normalized_name"] = existing_skill.normalized_name
                skill["category"] = existing_skill.category
            else:
                new_skill = Skill.get_or_create(
                    name=skill["name"],
                    category=skill.get("category", "other"),
                )
                skill["skill_id"] = new_skill.id
                skill["normalized_name"] = new_skill.normalized_name

            normalized_skills.append(skill)

        logger.info(f"Normalized {len(normalized_skills)} skills")
        return normalized_skills

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    def generate_embedding(self, text: str) -> List[float]:
        if not self.model:
            raise RuntimeError("Model not loaded")

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def store_embedding(self, resume_id: str, embedding: List[float], user_id: str):
        try:
            from qdrant_client.models import PointStruct

            point = PointStruct(
                id=resume_id,
                vector=embedding,
                payload={
                    "user_id": user_id,
                    "resume_id": resume_id,
                    "type": "resume",
                },
            )

            # ✅ FIXED: use live extensions reference
            extensions.qdrant_client.upsert(
                collection_name="resume_embeddings",
                points=[point],
            )

            logger.info(f"Stored embedding for resume: {resume_id}")

        except Exception as e:
            logger.error(f"Failed to store embedding: {e}")
            raise

    # ------------------------------------------------------------------
    # Full Processing Pipeline
    # ------------------------------------------------------------------

    def process_resume(self, resume_id: str) -> Dict:
        resume = Resume.query.get(resume_id)
        if not resume:
            raise ValueError(f"Resume not found: {resume_id}")

        try:
            resume.processing_status = "processing"
            db.session.commit()

            file_path = resume.file_url
            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"Resume file not found: {file_path}"
                )

            with open(file_path, "rb") as f:
                file_content = f.read()

            parsed = self.parse_resume(file_content, resume.file_type)
            resume.raw_text = parsed["text"]

            sections = extract_resume_sections(parsed["text"])
            resume.parsed_data = {
                "metadata": parsed["metadata"],
                "sections": sections,
            }

            extracted_skills = self.extract_skills(parsed["text"])
            normalized_skills = self.normalize_skills(extracted_skills)
            resume.extracted_skills = normalized_skills

            for skill in normalized_skills:
                user_skill = UserSkill(
                    user_id=resume.user_id,
                    skill_id=skill["skill_id"],
                    proficiency=min(
                        5, max(1, skill.get("mentions", 1))
                    ),
                    is_verified=False,
                    source="resume",
                )
                db.session.add(user_skill)

            embedding = self.generate_embedding(parsed["text"])
            self.store_embedding(resume_id, embedding, resume.user_id)

            resume.processing_status = "completed"
            db.session.commit()

            logger.info(
                f"Resume processing completed: {resume_id}"
            )

            return {
                "success": True,
                "skills_extracted": len(normalized_skills),
                "skills": normalized_skills,
            }

        except Exception as e:
            resume.processing_status = "failed"
            resume.processing_error = str(e)
            db.session.commit()

            logger.error(f"Resume processing failed: {e}")
            raise


# ----------------------------------------------------------------------
# Singleton
# ----------------------------------------------------------------------

_resume_agent = None


def get_resume_agent() -> ResumeAgent:
    global _resume_agent
    if _resume_agent is None:
        _resume_agent = ResumeAgent()
    return _resume_agent