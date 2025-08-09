import re
import spacy
from collections import Counter
from typing import List, Dict, Set

class AdvancedCVMatcher:
    """Advanced CV matcher with better text analysis and skill extraction"""
    
    def __init__(self, cv_path: str):
        self.cv_path = cv_path
        
        # Try to load spacy model first
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            print("⚠️ spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Initialize Ollama client
        try:
            from ollama_client import ollama_client
            self.ollama_client = ollama_client
            if self.ollama_client.available:
                print("✅ Ollama client available for CV matching.")
            else:
                print("⚠️ Ollama client not available for CV matching.")
        except ImportError:
            self.ollama_client = None
            print("⚠️ Ollama client not found. LLM-based matching will be disabled.")
        
        # Now extract CV data
        self.cv_text = self.extract_cv_text()
        self.cv_skills = self.extract_skills_advanced()
        self.cv_keywords = self.extract_keywords()

    def extract_cv_text(self) -> str:
        """Enhanced text extraction from CV/Resume"""
        text = ""
        
        try:
            if self.cv_path.endswith('.pdf'):
                # Try multiple PDF libraries
                try:
                    import PyPDF2
                    with open(self.cv_path, 'rb') as file:
                        reader = PyPDF2.PdfReader(file)
                        for page in reader.pages:
                            text += page.extract_text() + "\n"
                except:
                    try:
                        import pdfplumber
                        with pdfplumber.open(self.cv_path) as pdf:
                            for page in pdf.pages:
                                text += page.extract_text() + "\n"
                    except:
                        print("⚠️ Could not extract PDF text. Install PyPDF2 or pdfplumber")
                        
            elif self.cv_path.endswith('.docx'):
                try:
                    from docx import Document
                    doc = Document(self.cv_path)
                    text = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
                except:
                    print("⚠️ Could not extract DOCX text. Install python-docx")
                    
            else:
                # Text file
                with open(self.cv_path, 'r', encoding='utf-8') as file:
                    text = file.read()
                    
        except Exception as e:
            print(f"❌ Error reading CV: {e}")
            
        return text
    
    def extract_skills_advanced(self) -> Set[str]:
        """Advanced skill extraction with comprehensive skill database"""
        # Comprehensive skill database
        skill_categories = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
                'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell'
            ],
            'web_technologies': [
                'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
                'spring', 'laravel', 'rails', 'asp.net', 'jquery', 'bootstrap', 'sass', 'less'
            ],
            'databases': [
                'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'oracle',
                'sqlite', 'cassandra', 'dynamodb', 'neo4j', 'influxdb'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'amazon web services', 'microsoft azure',
                'heroku', 'digitalocean', 'linode', 'vultr'
            ],
            'devops_tools': [
                'docker', 'kubernetes', 'jenkins', 'gitlab ci', 'github actions', 'ansible',
                'terraform', 'vagrant', 'chef', 'puppet', 'nagios', 'prometheus'
            ],
            'data_science': [
                'machine learning', 'deep learning', 'ai', 'artificial intelligence', 'pandas',
                'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras', 'jupyter', 'tableau',
                'power bi', 'spark', 'hadoop', 'kafka'
            ],
            'version_control': [
                'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial'
            ],
            'methodologies': [
                'agile', 'scrum', 'kanban', 'devops', 'ci/cd', 'tdd', 'bdd', 'microservices',
                'rest api', 'graphql', 'soap'
            ],
            'soft_skills': [
                'leadership', 'teamwork', 'communication', 'problem solving', 'critical thinking',
                'project management', 'mentoring', 'training'
            ]
        }
        
        cv_lower = self.cv_text.lower()
        found_skills = set()
        
        # Extract skills from all categories
        for category, skills in skill_categories.items():
            for skill in skills:
                if skill in cv_lower:
                    found_skills.add(skill)
        
        # Use spaCy for named entity recognition if available
        if self.nlp:
            try:
                doc = self.nlp(self.cv_text)
                for ent in doc.ents:
                    if ent.label_ in ['ORG', 'PRODUCT']:  # Organizations and products might be technologies
                        skill_candidate = ent.text.lower()
                        # Check if it's a known technology
                        for category, skills in skill_categories.items():
                            if skill_candidate in skills:
                                found_skills.add(skill_candidate)
            except Exception as e:
                print(f"Error in NLP processing: {e}")
        
        return found_skills
    
    def extract_keywords(self) -> List[str]:
        """Extract important keywords from CV"""
        # Common stop words to exclude
        stop_words = {
            'and', 'or', 'but', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'under', 'between', 'among', 'throughout', 'despite', 'towards',
            'upon', 'concerning', 'regarding', 'according'
        }
        
        # Extract words, filter and count
        words = re.findall(r'\b[a-zA-Z]{3,}\b', self.cv_text.lower())
        filtered_words = [word for word in words if word not in stop_words]
        
        # Get most common words
        word_counts = Counter(filtered_words)
        return [word for word, count in word_counts.most_common(50)]
    
    def calculate_llm_match_score(self, job_description: str, job_title: str) -> float:
        """
        Calculates a match score using a local LLM.
        """
        if not self.ollama_client or not self.ollama_client.available or not self.cv_text:
            return 0.0

        try:
            # Prepare a summary of the CV to keep the prompt concise
            cv_summary = self.cv_text[:2000] # Use first 2000 chars of CV

            system_prompt = """
            You are an expert career advisor and CV analyst. Your task is to evaluate how well a candidate's CV matches a job description.
            Analyze the provided CV summary and job details, then provide a match score from 0.0 to 1.0, where 1.0 is a perfect match.
            Respond ONLY with a JSON object with a single key "match_score". Example: {"match_score": 0.85}
            """
            
            prompt = f"""
            CV Summary:
            ---
            {cv_summary}
            ---

            Job Posting:
            ---
            Title: {job_title}
            Description: {job_description[:2000]}
            ---

            Based on the CV summary, how well does this candidate match the job posting?
            Provide your score in a JSON object.
            """

            response = self.ollama_client.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=100,
                temperature=0.1
            )

            if response:
                import json
                try:
                    # Clean response
                    clean_response = response.strip()
                    if clean_response.startswith("```json"):
                        clean_response = clean_response[7:]
                    if clean_response.startswith("```"):
                        clean_response = clean_response[3:]
                    if clean_response.endswith("```"):
                        clean_response = clean_response[:-3]
                    
                    assessment = json.loads(clean_response)
                    score = assessment.get('match_score', 0.0)
                    if isinstance(score, (float, int)):
                        return float(score)
                except (json.JSONDecodeError, TypeError):
                    print(f"⚠️ Could not parse LLM match score response: {response}")
                    # Fallback to simple regex if possible
                    import re
                    match = re.search(r'(\\d\\.\\d+|\\d+)', response)
                    if match:
                        try:
                            return float(match.group())
                        except ValueError:
                            pass

            return 0.0
        except Exception as e:
            print(f"❌ Error during LLM match score calculation: {e}")
            return 0.0

    def calculate_match_score(self, job_description: str, job_title: str = "") -> Dict:
        """Advanced match score calculation with detailed breakdown"""
        if not job_description or not self.cv_text:
            return {'total_score': 0.0, 'breakdown': {}}
        
        job_lower = job_description.lower()
        job_title_lower = job_title.lower()
        cv_lower = self.cv_text.lower()
        
        # 1. Skill matching (40% weight)
        job_skills = set()
        for skill in self.cv_skills:
            if skill in job_lower or skill in job_title_lower:
                job_skills.add(skill)
        
        skill_score = len(job_skills) / len(self.cv_skills) if self.cv_skills else 0
        
        # 2. Keyword matching (30% weight)
        job_keywords = set(re.findall(r'\b[a-zA-Z]{3,}\b', job_lower))
        cv_keywords = set(self.cv_keywords)
        common_keywords = job_keywords.intersection(cv_keywords)
        
        keyword_score = len(common_keywords) / len(job_keywords) if job_keywords else 0
        
        # 3. Enhanced Title relevance (30% weight - increased for better filtering)
        title_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', job_title_lower))
        cv_title_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', cv_lower[:500]))  # First 500 chars likely contain title/summary
        title_matches = title_words.intersection(cv_title_words)
        
        # Base title score
        title_score = len(title_matches) / len(title_words) if title_words else 0
        
        # Enhanced title relevance check - heavily penalize irrelevant job categories
        irrelevant_job_indicators = [
            'sales', 'marketing', 'designer', 'support', 'customer', 'service',
            'recruiter', 'hr', 'human', 'finance', 'accounting', 'secretary',
            'assistant', 'coordinator', 'nurse', 'teacher', 'doctor', 'therapist',
            'waiter', 'chef', 'cashier', 'retail', 'store'
        ]
        
        # If job title contains irrelevant indicators, heavily penalize
        if any(indicator in job_title_lower for indicator in irrelevant_job_indicators):
            title_score = 0.0  # Zero out score for irrelevant job categories
        
        # Bonus for highly relevant IT/system keywords
        it_keywords = [
            'system', 'administrator', 'engineer', 'integration', 'infrastructure',
            'devops', 'network', 'security', 'cloud', 'server', 'linux', 'windows'
        ]
        it_bonus = sum(1 for keyword in it_keywords if keyword in job_title_lower)
        if it_bonus >= 2:  # Multiple IT keywords
            title_score = min(1.0, title_score + 0.3)  # Bonus for IT roles
        
        # 4. Experience level matching (10% weight)
        experience_indicators = ['senior', 'lead', 'principal', 'architect', 'manager', 'director', 'junior', 'entry']
        job_exp_level = [word for word in experience_indicators if word in job_lower]
        cv_exp_level = [word for word in experience_indicators if word in cv_lower]
        
        exp_score = 1.0 if any(exp in cv_exp_level for exp in job_exp_level) else 0.5
        
        # Calculate weighted final score (updated weights for better relevance)
        algorithmic_score = (
            skill_score * 0.3 +      # Reduced from 40% to 30%
            keyword_score * 0.2 +    # Reduced from 30% to 20%  
            title_score * 0.4 +      # Increased from 20% to 40% for better job filtering
            exp_score * 0.1          # Kept at 10%
        )
        
        # Get LLM score
        llm_score = self.calculate_llm_match_score(job_description, job_title)

        # Combine scores (e.g., 70% algorithmic, 30% LLM)
        final_score = (algorithmic_score * 0.7) + (llm_score * 0.3)
        
        # Cap at 1.0
        final_score = min(final_score, 1.0)
        
        return {
            'total_score': final_score,
            'breakdown': {
                'algorithmic_score': algorithmic_score,
                'llm_score': llm_score,
                'skill_score': skill_score,
                'keyword_score': keyword_score,
                'title_score': title_score,
                'experience_score': exp_score,
                'matched_skills': list(job_skills),
                'matched_keywords': list(common_keywords)[:10],  # Top 10
                'skill_count': len(self.cv_skills),
                'matched_skill_count': len(job_skills)
            }
        }
    
    def get_skills_summary(self) -> Dict:
        """Get summary of extracted skills by category"""
        # Categorize found skills
        skill_categories = {
            'Programming': ['python', 'java', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go'],
            'Web Development': ['html', 'css', 'react', 'angular', 'vue', 'node.js', 'django', 'flask'],
            'Databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis'],
            'Cloud': ['aws', 'azure', 'gcp', 'docker', 'kubernetes'],
            'Data Science': ['machine learning', 'pandas', 'numpy', 'tensorflow', 'pytorch'],
            'Tools': ['git', 'jenkins', 'ansible', 'terraform']
        }
        
        categorized_skills = {}
        for category, category_skills in skill_categories.items():
            found_in_category = [skill for skill in self.cv_skills if skill in category_skills]
            if found_in_category:
                categorized_skills[category] = found_in_category
        
        # Add uncategorized skills
        all_categorized = set()
        for skills in categorized_skills.values():
            all_categorized.update(skills)
        
        uncategorized = [skill for skill in self.cv_skills if skill not in all_categorized]
        if uncategorized:
            categorized_skills['Other'] = uncategorized
        
        return categorized_skills 