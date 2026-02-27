"""Career Roadmap Service for generating personalized career growth plans."""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import structlog

from app.models.resume import Resume
from app.services.skill_analytics_service import SkillAnalyticsService
from app.services.domain_detection_service import DomainDetectionService
from app.services.seniority_service import SeniorityService

logger = structlog.get_logger()


@dataclass
class RoadmapMilestone:
    """A milestone in the career roadmap."""
    order: int
    title: str
    description: str
    reason: str
    skills_to_acquire: List[str]
    estimated_weeks: int
    resources: List[Dict]
    completion_criteria: str


@dataclass
class CareerRoadmap:
    """Complete career roadmap."""
    current_position: str
    target_position: str
    current_domain: str
    estimated_timeline_months: int
    milestones: List[RoadmapMilestone]
    summary: str


class RoadmapService:
    """
    Generates personalized career roadmaps based on:
    - Current domain and seniority
    - Skill gaps
    - Market demand
    - Career progression paths
    """

    # Learning resources database (simplified)
    LEARNING_RESOURCES = {
        'docker': [
            {'name': 'Docker Documentation', 'url': 'https://docs.docker.com/', 'type': 'official'},
            {'name': 'Docker Mastery on Udemy', 'url': 'https://www.udemy.com/course/docker-mastery/', 'type': 'course'}
        ],
        'kubernetes': [
            {'name': 'Kubernetes Basics', 'url': 'https://kubernetes.io/docs/tutorials/', 'type': 'official'},
            {'name': 'CKAD Certification', 'url': 'https://www.cncf.io/certification/ckad/', 'type': 'certification'}
        ],
        'aws': [
            {'name': 'AWS Free Tier', 'url': 'https://aws.amazon.com/free/', 'type': 'practice'},
            {'name': 'AWS Solutions Architect', 'url': 'https://aws.amazon.com/certification/', 'type': 'certification'}
        ],
        'python': [
            {'name': 'Python Official Tutorial', 'url': 'https://docs.python.org/3/tutorial/', 'type': 'official'}
        ],
        'machine learning': [
            {'name': 'Fast.ai Course', 'url': 'https://www.fast.ai/', 'type': 'course'},
            {'name': 'Andrew Ng ML Course', 'url': 'https://www.coursera.org/learn/machine-learning', 'type': 'course'}
        ],
        'react': [
            {'name': 'React Documentation', 'url': 'https://react.dev/', 'type': 'official'},
            {'name': 'Epic React', 'url': 'https://epicreact.dev/', 'type': 'course'}
        ],
        'typescript': [
            {'name': 'TypeScript Handbook', 'url': 'https://www.typescriptlang.org/docs/', 'type': 'official'}
        ],
        'sql': [
            {'name': 'SQLZoo', 'url': 'https://sqlzoo.net/', 'type': 'practice'},
            {'name': 'Mode Analytics SQL', 'url': 'https://mode.com/sql-tutorial/', 'type': 'tutorial'}
        ],
        'git': [
            {'name': 'Git Documentation', 'url': 'https://git-scm.com/doc', 'type': 'official'},
            {'name': 'Learn Git Branching', 'url': 'https://learngitbranching.js.org/', 'type': 'interactive'}
        ]
    }

    # Career progression paths
    CAREER_PATHS = {
        'Machine Learning / AI': {
            'Entry-Level': ['Junior ML Engineer', 'Data Scientist (Junior)', 'AI Research Assistant'],
            'Junior': ['ML Engineer', 'Data Scientist', 'Applied Scientist'],
            'Mid-Level': ['Senior ML Engineer', 'Senior Data Scientist', 'ML Architect'],
            'Senior': ['Staff ML Engineer', 'Principal Data Scientist', 'ML Engineering Manager'],
            'Lead': ['Director of ML', 'Head of AI', 'Chief Scientist']
        },
        'Backend Engineering': {
            'Entry-Level': ['Junior Backend Developer', 'API Developer'],
            'Junior': ['Backend Developer', 'Software Engineer'],
            'Mid-Level': ['Senior Backend Engineer', 'Platform Engineer'],
            'Senior': ['Staff Engineer', 'Principal Engineer'],
            'Lead': ['Engineering Manager', 'Director of Engineering']
        },
        'Frontend Engineering': {
            'Entry-Level': ['Junior Frontend Developer', 'UI Developer'],
            'Junior': ['Frontend Developer', 'React Developer'],
            'Mid-Level': ['Senior Frontend Engineer', 'UI Architect'],
            'Senior': ['Staff Frontend Engineer', 'Principal UI Engineer'],
            'Lead': ['Frontend Engineering Manager', 'Director of Product Engineering']
        },
        'Data Engineering': {
            'Entry-Level': ['Junior Data Engineer', 'ETL Developer'],
            'Junior': ['Data Engineer', 'Pipeline Engineer'],
            'Mid-Level': ['Senior Data Engineer', 'Data Platform Engineer'],
            'Senior': ['Staff Data Engineer', 'Data Architect'],
            'Lead': ['Head of Data Engineering', 'Director of Data Platform']
        },
        'DevOps / SRE': {
            'Entry-Level': ['Junior DevOps Engineer', 'System Administrator'],
            'Junior': ['DevOps Engineer', 'Site Reliability Engineer'],
            'Mid-Level': ['Senior DevOps Engineer', 'Senior SRE'],
            'Senior': ['Staff SRE', 'Platform Architect'],
            'Lead': ['Head of Infrastructure', 'Director of Platform Engineering']
        },
        'Full Stack Development': {
            'Entry-Level': ['Junior Full Stack Developer', 'Web Developer'],
            'Junior': ['Full Stack Developer', 'Software Engineer'],
            'Mid-Level': ['Senior Full Stack Engineer', 'Product Engineer'],
            'Senior': ['Staff Engineer', 'Technical Lead'],
            'Lead': ['Engineering Manager', 'Director of Engineering']
        },
        'Mobile Development': {
            'Entry-Level': ['Junior Mobile Developer', 'iOS/Android Developer'],
            'Junior': ['Mobile Developer', 'App Developer'],
            'Mid-Level': ['Senior Mobile Engineer', 'Mobile Architect'],
            'Senior': ['Staff Mobile Engineer', 'Principal Mobile Developer'],
            'Lead': ['Mobile Engineering Manager', 'Director of Mobile']
        }
    }

    @classmethod
    def _get_resources_for_skill(cls, skill: str) -> List[Dict]:
        """Get learning resources for a skill."""
        skill_lower = skill.lower()
        
        # Direct match
        if skill_lower in cls.LEARNING_RESOURCES:
            return cls.LEARNING_RESOURCES[skill_lower]
        
        # Partial match
        for key, resources in cls.LEARNING_RESOURCES.items():
            if key in skill_lower or skill_lower in key:
                return resources
        
        # Default resources
        return [
            {'name': f'Learn {skill}', 'url': f'https://www.google.com/search?q=learn+{skill}', 'type': 'search'}
        ]

    @classmethod
    def _estimate_learning_weeks(cls, skill: str, demand_percentage: float) -> int:
        """Estimate weeks needed to learn a skill."""
        # Base estimates by skill type
        base_weeks = {
            'docker': 2,
            'kubernetes': 4,
            'aws': 6,
            'python': 4,
            'javascript': 4,
            'typescript': 3,
            'react': 4,
            'sql': 3,
            'git': 1,
            'machine learning': 12,
            'deep learning': 16,
            'tensorflow': 6,
            'pytorch': 6
        }
        
        skill_lower = skill.lower()
        base = 4  # Default
        
        for key, weeks in base_weeks.items():
            if key in skill_lower or skill_lower in key:
                base = weeks
                break
        
        # Adjust based on demand (high demand skills might need more depth)
        if demand_percentage >= 50:
            base = int(base * 1.2)
        
        return max(1, base)

    @classmethod
    def _get_target_position(cls, domain: str, current_level: str) -> str:
        """Get the next target position based on domain and current level."""
        next_level = SeniorityService.get_next_career_level(current_level)
        
        if not next_level:
            return f"Principal {domain.split('/')[0].strip()}"
        
        domain_paths = cls.CAREER_PATHS.get(domain, {})
        positions = domain_paths.get(next_level, [f"{next_level} {domain.split('/')[0].strip()}"])
        
        return positions[0] if positions else f"{next_level} Engineer"

    @classmethod
    def generate_roadmap(cls, user_id: str) -> Optional[CareerRoadmap]:
        """
        Generate a personalized career roadmap for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            CareerRoadmap or None if generation fails
        """
        try:
            # Get user data
            resume = (
                Resume.query
                .filter_by(user_id=user_id, processing_status='completed')
                .order_by(Resume.created_at.desc())
                .first()
            )
            
            if not resume or not resume.raw_text:
                return None
            
            # Detect domain and seniority
            domain_result = DomainDetectionService.detect_domain(resume.raw_text)
            seniority_result = SeniorityService.detect_seniority(resume)
            
            if not domain_result:
                return None
            
            current_domain = domain_result.primary_domain
            current_level = seniority_result.seniority_level
            
            # Get skill gaps
            skill_gaps = SkillAnalyticsService.analyze_user_skill_gaps(user_id)
            
            # Filter to high-priority gaps
            high_priority_gaps = [g for g in skill_gaps if g.priority in ['high', 'medium']][:5]
            
            # Build milestones
            milestones = []
            current_order = 1
            total_weeks = 0
            
            # Milestone 1: Foundation skills (if needed)
            if seniority_result.estimated_years < 2:
                milestones.append(RoadmapMilestone(
                    order=current_order,
                    title='Build Core Technical Foundation',
                    description='Strengthen fundamental programming and computer science skills',
                    reason='Strong fundamentals are essential for career growth',
                    skills_to_acquire=['Data Structures', 'Algorithms', 'System Design Basics'],
                    estimated_weeks=8,
                    resources=[
                        {'name': 'LeetCode', 'url': 'https://leetcode.com/', 'type': 'practice'},
                        {'name': 'System Design Primer', 'url': 'https://github.com/donnemartin/system-design-primer', 'type': 'github'}
                    ],
                    completion_criteria='Solve 50 LeetCode problems and understand basic system design concepts'
                ))
                current_order += 1
                total_weeks += 8
            
            # Milestone 2: High-demand skill acquisition
            if high_priority_gaps:
                top_gap = high_priority_gaps[0]
                milestones.append(RoadmapMilestone(
                    order=current_order,
                    title=f"Master {top_gap.skill.title()}",
                    description=f"Learn {top_gap.skill} - required by {top_gap.demand_percentage}% of jobs",
                    reason=f"High market demand ({top_gap.demand_percentage}%) - unlocks {top_gap.job_count} job opportunities",
                    skills_to_acquire=[top_gap.skill],
                    estimated_weeks=cls._estimate_learning_weeks(top_gap.skill, top_gap.demand_percentage),
                    resources=cls._get_resources_for_skill(top_gap.skill),
                    completion_criteria=f'Build a project using {top_gap.skill} and deploy it'
                ))
                current_order += 1
                total_weeks += cls._estimate_learning_weeks(top_gap.skill, top_gap.demand_percentage)
            
            # Milestone 3: Second high-demand skill
            if len(high_priority_gaps) > 1:
                second_gap = high_priority_gaps[1]
                milestones.append(RoadmapMilestone(
                    order=current_order,
                    title=f"Add {second_gap.skill.title()} to Your Toolkit",
                    description=f"Expand your expertise with {second_gap.skill}",
                    reason=f"Complements your primary skills and increases marketability",
                    skills_to_acquire=[second_gap.skill],
                    estimated_weeks=cls._estimate_learning_weeks(second_gap.skill, second_gap.demand_percentage),
                    resources=cls._get_resources_for_skill(second_gap.skill),
                    completion_criteria=f'Integrate {second_gap.skill} with your existing projects'
                ))
                current_order += 1
                total_weeks += cls._estimate_learning_weeks(second_gap.skill, second_gap.demand_percentage)
            
            # Milestone 4: Portfolio/Project milestone
            milestones.append(RoadmapMilestone(
                order=current_order,
                title='Build a Production-Ready Project',
                description=f'Create a comprehensive project showcasing your {current_domain} skills',
                reason='Practical experience demonstrates your capabilities to employers',
                skills_to_acquire=['Project Management', 'Documentation', 'Deployment'],
                estimated_weeks=4,
                resources=[
                    {'name': 'GitHub', 'url': 'https://github.com/', 'type': 'platform'},
                    {'name': 'Portfolio Tips', 'url': 'https://www.freecodecamp.org/news/build-a-developer-portfolio/', 'type': 'article'}
                ],
                completion_criteria='Complete project with documentation, tests, and deployed demo'
            ))
            current_order += 1
            total_weeks += 4
            
            # Milestone 5: Interview preparation (for next level)
            next_level = SeniorityService.get_next_career_level(current_level)
            if next_level:
                milestones.append(RoadmapMilestone(
                    order=current_order,
                    title=f'Prepare for {next_level} Interviews',
                    description=f'Study advanced topics and practice interview questions for {next_level} roles',
                    reason=f'Interview preparation is crucial for leveling up to {next_level}',
                    skills_to_acquire=['System Design', 'Behavioral Interviewing', 'Salary Negotiation'],
                    estimated_weeks=3,
                    resources=[
                        {'name': 'Interviewing.io', 'url': 'https://interviewing.io/', 'type': 'practice'},
                        {'name': 'Levels.fyi', 'url': 'https://www.levels.fyi/', 'type': 'research'}
                    ],
                    completion_criteria='Complete 5 mock interviews and study system design'
                ))
                total_weeks += 3
            
            # Calculate target position
            target_position = cls._get_target_position(current_domain, current_level)
            
            # Generate summary
            summary = (
                f"You're currently a {current_level} in {current_domain}. "
                f"This roadmap will help you grow into a {target_position} role over the next {total_weeks // 4} months. "
                f"Focus on acquiring high-demand skills and building practical projects to demonstrate your expertise."
            )
            
            return CareerRoadmap(
                current_position=f"{current_level} in {current_domain}",
                target_position=target_position,
                current_domain=current_domain,
                estimated_timeline_months=total_weeks // 4,
                milestones=milestones,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Failed to generate roadmap: {e}")
            return None

    @classmethod
    def get_roadmap_summary(cls, user_id: str) -> Dict:
        """
        Get a simplified roadmap summary.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with roadmap summary
        """
        roadmap = cls.generate_roadmap(user_id)
        
        if not roadmap:
            return {
                'available': False,
                'message': 'Upload a resume to generate your career roadmap'
            }
        
        return {
            'available': True,
            'current_position': roadmap.current_position,
            'target_position': roadmap.target_position,
            'timeline_months': roadmap.estimated_timeline_months,
            'milestones_count': len(roadmap.milestones),
            'next_milestone': {
                'title': roadmap.milestones[0].title,
                'description': roadmap.milestones[0].description,
                'estimated_weeks': roadmap.milestones[0].estimated_weeks
            } if roadmap.milestones else None,
            'summary': roadmap.summary
        }
