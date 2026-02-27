export interface User {
  id: string;
  email: string;
  phone?: string;
  display_name?: string;
  photo_url?: string;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string;
}

export interface Skill {
  id: string;
  name: string;
  normalized_name: string;
  category?: string;
  description?: string;
  aliases?: string[];
  parent_id?: string;
  created_at: string;
  updated_at: string;
}

export interface UserSkill {
  id: string;
  user_id: string;
  skill_id: string;
  skill_name?: string;
  proficiency: number;
  is_verified: boolean;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  success: boolean;
  data?: {
    access_token: string;
    refresh_token: string;
    user: User;
  };
  error?: string;
  message?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export type Theme = 'light' | 'dark' | 'system';

export interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: 'light' | 'dark';
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

// AI Career Mentor Types

export interface JobMatch {
  job: {
    id: string;
    title: string;
    company: { name: string } | null;
    location: string;
    is_remote: boolean;
    employment_type: string;
    description?: string;
    requirements?: string;
    responsibilities?: string;
    required_skills?: string[];
    source_platform?: string;
    source_url?: string;
  };
  final_score: number;
  breakdown: {
    semantic_score: number;
    skill_overlap: number;
    freshness_score: number;
    experience_match: number;
  };
  matching_skills: string[];
  missing_skills: string[];
  freshness_days: number | null;
  experience_alignment: string;
  explanation: string;
}

export interface DomainResult {
  primary_domain: string;
  primary_confidence: number;
  secondary_domain: string | null;
  secondary_confidence: number;
  all_scores: Record<string, number>;
}

export interface SeniorityResult {
  seniority_level: string;
  estimated_years: number;
  confidence: number;
  years_breakdown: Record<string, number>;
  next_level: string | null;
  level_requirements: {
    years_range: string;
    typical_titles: string[];
    key_expectations: string[];
  };
}

export interface SkillGap {
  skill: string;
  demand_percentage: number;
  job_count: number;
  priority: 'high' | 'medium' | 'low';
}

export interface SkillGapAnalysis {
  market_demand: Record<string, {
    demand_percentage: number;
    job_count: number;
    total_jobs: number;
  }>;
  user_skills: string[];
  skill_coverage: {
    percentage: number;
    covered_count: number;
    total_high_demand: number;
  };
  gaps: SkillGap[];
  top_opportunities: {
    skill: string;
    demand_percentage: number;
    potential_jobs: number;
  }[];
}

export interface ProfileStrength {
  profile_strength: number;
  improvement_potential: number;
  breakdown: {
    resume_completeness: number;
    skill_coverage: number;
    match_rate: number;
    market_alignment: number;
  };
  suggestions: string[];
}

export interface MatchAnalytics {
  total_jobs_analyzed: number;
  high_match_jobs: number;
  average_match_score: number;
  improvement: {
    previous_average: number;
    current_average: number;
    change_percent: number;
  };
  match_distribution: {
    excellent: number;
    good: number;
    fair: number;
    poor: number;
  };
  recent_matches: {
    job_id: string;
    job_title: string;
    company: string | null;
    match_score: number;
    matching_skills: string[];
    missing_skills: string[];
  }[];
  recommendations: {
    type: string;
    priority: 'high' | 'medium' | 'low';
    message: string;
    action: string;
  }[];
}

export interface RoadmapMilestone {
  order: number;
  title: string;
  description: string;
  reason: string;
  skills_to_acquire: string[];
  estimated_weeks: number;
  resources: {
    name: string;
    url: string;
    type: string;
  }[];
  completion_criteria: string;
}

export interface CareerRoadmap {
  current_position: string;
  target_position: string;
  current_domain: string;
  estimated_timeline_months: number;
  summary: string;
  milestones: RoadmapMilestone[];
}

export interface RoadmapSummary {
  available: boolean;
  message?: string;
  current_position?: string;
  target_position?: string;
  timeline_months?: number;
  milestones_count?: number;
  next_milestone?: {
    title: string;
    description: string;
    estimated_weeks: number;
  };
  summary?: string;
}
