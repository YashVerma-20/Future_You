"""Seniority Detection Service for determining experience level from resume."""
import re
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

from app.models.resume import Resume

logger = structlog.get_logger()


@dataclass
class SeniorityResult:
    """Result of seniority detection."""
    seniority_level: str
    estimated_years: float
    confidence: float
    years_breakdown: Dict[str, float]


class SeniorityService:
    """
    Detects seniority level from resume experience and content.
    """

    # Seniority level keywords and their weights
    SENIORITY_KEYWORDS = {
        'entry': {
            'keywords': ['entry level', 'entry-level', 'junior', 'intern', 'internship',
                        'trainee', 'fresher', 'graduate', '0-1 years', '0-2 years'],
            'level': 1,
            'typical_years': (0, 1)
        },
        'junior': {
            'keywords': ['junior', 'associate', '1-2 years', '1-3 years', 'early career'],
            'level': 2,
            'typical_years': (1, 3)
        },
        'mid': {
            'keywords': ['mid', 'mid-level', 'intermediate', '2-5 years', '3-5 years',
                        'experienced', 'professional'],
            'level': 3,
            'typical_years': (3, 5)
        },
        'senior': {
            'keywords': ['senior', 'sr.', 'sr ', '5+ years', '5-8 years', '6+ years',
                        'advanced', 'specialist'],
            'level': 4,
            'typical_years': (5, 8)
        },
        'lead': {
            'keywords': ['lead', 'leader', 'tech lead', 'technical lead', 'team lead',
                        '8+ years', '7+ years'],
            'level': 5,
            'typical_years': (7, 10)
        },
        'principal': {
            'keywords': ['principal', 'staff', 'architect', '10+ years', '8-12 years'],
            'level': 6,
            'typical_years': (10, 15)
        },
        'executive': {
            'keywords': ['director', 'vp', 'vice president', 'cto', 'chief', 'head of',
                        '15+ years', 'executive'],
            'level': 7,
            'typical_years': (15, 30)
        }
    }

    # Patterns for extracting years
    YEAR_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*(?:\+)?\s*years?',
        r'(\d+(?:\.\d+)?)\s*-\s*\d+\s*years?',
        r'(\d{4})\s*-\s*(?:present|current|now|\d{4})',
    ]

    @classmethod
    def _extract_years_from_experience(cls, experience_entries: List[Dict]) -> float:
        """
        Extract total years of experience from experience entries.
        
        Args:
            experience_entries: List of experience dictionaries
            
        Returns:
            Total years of experience
        """
        total_years = 0.0
        current_year = datetime.now().year

        for entry in experience_entries:
            # Direct years field
            if 'years' in entry and entry['years']:
                try:
                    total_years += float(entry['years'])
                    continue
                except (ValueError, TypeError):
                    pass

            # Date range extraction
            start_date = entry.get('start_date')
            end_date = entry.get('end_date')

            if start_date:
                try:
                    # Try to parse year from date string
                    start_year = None
                    end_year = current_year

                    if isinstance(start_date, str):
                        # Try various formats
                        for fmt in ['%Y-%m-%d', '%Y', '%m/%Y', '%B %Y']:
                            try:
                                parsed = datetime.strptime(start_date, fmt)
                                start_year = parsed.year
                                break
                            except ValueError:
                                continue

                        # Extract year directly if format is unknown
                        if start_year is None:
                            year_match = re.search(r'(20\d{2}|19\d{2})', start_date)
                            if year_match:
                                start_year = int(year_match.group(1))

                    if isinstance(start_date, datetime):
                        start_year = start_date.year

                    # Parse end date
                    if end_date:
                        if isinstance(end_date, str):
                            if end_date.lower() in ['present', 'current', 'now']:
                                end_year = current_year
                            else:
                                for fmt in ['%Y-%m-%d', '%Y', '%m/%Y', '%B %Y']:
                                    try:
                                        parsed = datetime.strptime(end_date, fmt)
                                        end_year = parsed.year
                                        break
                                    except ValueError:
                                        continue
                                else:
                                    year_match = re.search(r'(20\d{2}|19\d{2})', end_date)
                                    if year_match:
                                        end_year = int(year_match.group(1))

                        if isinstance(end_date, datetime):
                            end_year = end_date.year

                    if start_year and end_year:
                        years = end_year - start_year
                        if years > 0 and years < 50:  # Sanity check
                            total_years += years

                except Exception as e:
                    logger.debug(f"Failed to parse dates: {e}")
                    continue

        return total_years

    @classmethod
    def _detect_keywords_in_text(cls, text: str) -> Dict[str, int]:
        """
        Detect seniority keywords in text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary of level -> count
        """
        text_lower = text.lower()
        level_counts = {}

        for level_name, level_data in cls.SENIORITY_KEYWORDS.items():
            count = 0
            for keyword in level_data['keywords']:
                count += len(re.findall(r'\b' + re.escape(keyword) + r'\b', text_lower))
            level_counts[level_data['level']] = count

        return level_counts

    @classmethod
    def detect_seniority(cls, resume: Resume) -> SeniorityResult:
        """
        Detect seniority level from resume.
        
        Args:
            resume: Resume model instance
            
        Returns:
            SeniorityResult with level and estimated years
        """
        try:
            # Extract years from experience
            years_from_exp = cls._extract_years_from_experience(
                resume.extracted_experience or []
            )

            # Build full text from resume
            text_parts = []

            if resume.raw_text:
                text_parts.append(resume.raw_text)

            # Add experience titles
            for exp in resume.extracted_experience or []:
                if 'title' in exp:
                    text_parts.append(exp['title'])
                if 'description' in exp:
                    text_parts.append(exp['description'])

            full_text = ' '.join(text_parts)

            # Detect keywords
            keyword_counts = cls._detect_keywords_in_text(full_text)

            # Determine seniority from years
            if years_from_exp < 1:
                years_level = 1  # entry
            elif years_from_exp < 3:
                years_level = 2  # junior
            elif years_from_exp < 5:
                years_level = 3  # mid
            elif years_from_exp < 7:
                years_level = 4  # senior
            elif years_from_exp < 10:
                years_level = 5  # lead
            elif years_from_exp < 15:
                years_level = 6  # principal
            else:
                years_level = 7  # executive

            # Determine seniority from keywords
            keyword_level = 0
            max_count = 0
            for level, count in keyword_counts.items():
                if count > max_count:
                    max_count = count
                    keyword_level = level

            # Combine both signals
            if keyword_level > 0 and max_count >= 2:
                # Strong keyword signal
                final_level = keyword_level
                confidence = min(0.9, 0.6 + (max_count * 0.1))
            elif keyword_level > 0:
                # Weak keyword signal, blend with years
                final_level = round((years_level + keyword_level) / 2)
                confidence = 0.7
            else:
                # No keyword signal, rely on years
                final_level = years_level
                confidence = 0.6

            # Map level to name
            level_names = {
                1: 'Entry-Level',
                2: 'Junior',
                3: 'Mid-Level',
                4: 'Senior',
                5: 'Lead',
                6: 'Principal',
                7: 'Executive'
            }

            seniority_name = level_names.get(final_level, 'Mid-Level')

            # Adjust estimated years based on level
            if years_from_exp > 0:
                estimated_years = years_from_exp
            else:
                # Estimate from level
                typical = cls.SENIORITY_KEYWORDS.get(
                    seniority_name.lower().replace('-', '').replace(' ', ''),
                    {'typical_years': (3, 5)}
                )['typical_years']
                estimated_years = (typical[0] + typical[1]) / 2

            return SeniorityResult(
                seniority_level=seniority_name,
                estimated_years=round(estimated_years, 1),
                confidence=round(confidence, 2),
                years_breakdown={
                    'from_experience_entries': round(years_from_exp, 1),
                    'keyword_level': keyword_level,
                    'years_based_level': years_level
                }
            )

        except Exception as e:
            logger.error(f"Failed to detect seniority: {e}")
            return SeniorityResult(
                seniority_level='Mid-Level',
                estimated_years=3.0,
                confidence=0.3,
                years_breakdown={'error': str(e)}
            )

    @classmethod
    def detect_seniority_from_text(cls, text: str) -> Dict:
        """
        Quick seniority detection from text (for job descriptions).
        
        Args:
            text: Job description or other text
            
        Returns:
            Dictionary with detected level
        """
        keyword_counts = cls._detect_keywords_in_text(text)

        if not any(keyword_counts.values()):
            return {
                'seniority_level': 'Not Specified',
                'confidence': 0.0
            }

        # Find highest level with keywords
        max_level = max(keyword_counts.keys())
        max_count = keyword_counts[max_level]

        level_names = {
            1: 'Entry-Level',
            2: 'Junior',
            3: 'Mid-Level',
            4: 'Senior',
            5: 'Lead',
            6: 'Principal',
            7: 'Executive'
        }

        return {
            'seniority_level': level_names.get(max_level, 'Mid-Level'),
            'confidence': min(0.9, 0.5 + (max_count * 0.2))
        }

    @classmethod
    def get_next_career_level(cls, current_level: str) -> Optional[str]:
        """
        Get the next career level.
        
        Args:
            current_level: Current seniority level
            
        Returns:
            Next level name or None if at highest
        """
        levels = ['Entry-Level', 'Junior', 'Mid-Level', 'Senior', 'Lead', 'Principal', 'Executive']

        try:
            current_index = levels.index(current_level)
            if current_index < len(levels) - 1:
                return levels[current_index + 1]
        except ValueError:
            pass

        return None

    @classmethod
    def get_level_requirements(cls, level: str) -> Dict:
        """
        Get typical requirements for a seniority level.
        
        Args:
            level: Seniority level name
            
        Returns:
            Dictionary with requirements
        """
        requirements = {
            'Entry-Level': {
                'years_range': '0-1 years',
                'typical_titles': ['Junior Developer', 'Intern', 'Trainee'],
                'key_expectations': ['Learning fundamentals', 'Code reviews', 'Mentorship']
            },
            'Junior': {
                'years_range': '1-3 years',
                'typical_titles': ['Junior Engineer', 'Associate Developer'],
                'key_expectations': ['Independent work on tasks', 'Bug fixes', 'Feature development']
            },
            'Mid-Level': {
                'years_range': '3-5 years',
                'typical_titles': ['Software Engineer', 'Developer'],
                'key_expectations': ['Feature ownership', 'Code quality', 'Mentoring juniors']
            },
            'Senior': {
                'years_range': '5-8 years',
                'typical_titles': ['Senior Engineer', 'Senior Developer'],
                'key_expectations': ['System design', 'Architecture decisions', 'Cross-team collaboration']
            },
            'Lead': {
                'years_range': '7-10 years',
                'typical_titles': ['Tech Lead', 'Team Lead', 'Staff Engineer'],
                'key_expectations': ['Team leadership', 'Technical direction', 'Project planning']
            },
            'Principal': {
                'years_range': '10-15 years',
                'typical_titles': ['Principal Engineer', 'Architect'],
                'key_expectations': ['Organization-wide impact', 'Strategic decisions', 'Mentoring leads']
            },
            'Executive': {
                'years_range': '15+ years',
                'typical_titles': ['Director', 'VP Engineering', 'CTO'],
                'key_expectations': ['Business strategy', 'Organizational leadership', 'Industry influence']
            }
        }

        return requirements.get(level, requirements['Mid-Level'])
