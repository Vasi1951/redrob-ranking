import json
import os
import re
import time
import gzip
from datetime import datetime
from collections import Counter

def run_ranking(candidates_path, csv_out_path, json_out_path):
    start_time = time.time()
    
    # Compile regexes once for performance
    non_tech_patterns = [
        r"\bmarketing\b", r"\bsales\b", r"\bhr\b", r"\brecruiter\b", r"\btalent acquisition\b", 
        r"\bfinance\b", r"\bwriter\b", r"\bcontent\b", r"\baccountant\b", r"\boperations\b",
        r"\bhuman resources\b", r"\bproduct manager\b", r"\bproject manager\b", r"\bbusiness analyst\b",
        r"\bdesigner\b", r"\bui/ux\b", r"\bsocial media\b", r"\bsupport\b", r"\bcustomer service\b"
    ]
    non_tech_regex = re.compile("|".join(non_tech_patterns), re.IGNORECASE)

    tech_skills_keywords = [
        "python", "pytorch", "tensorflow", "ml", "machine learning", "deep learning", "nlp", 
        "rag", "embeddings", "vector search", "llm", "large language models", "sql", "spark",
        "airflow", "pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch",
        "faiss", "scikit-learn", "numpy", "pandas", "keras", "huggingface", "lora", "qlora",
        "peft", "aws", "gcp", "azure", "kubernetes", "docker", "git", "java", "c++", "scala"
    ]
    tech_skills_regex = re.compile("|".join([re.escape(k) for k in tech_skills_keywords]), re.IGNORECASE)

    # Core and nice-to-have skill weights
    SKILL_WEIGHTS = {
        # Core
        "embeddings": 3.0,
        "sentence-transformers": 3.0,
        "bge": 3.0,
        "e5": 3.0,
        "openai embeddings": 3.0,
        "vector database": 3.0,
        "pinecone": 3.0,
        "weaviate": 3.0,
        "qdrant": 3.0,
        "milvus": 3.0,
        "opensearch": 3.0,
        "elasticsearch": 2.0,
        "faiss": 3.0,
        "hybrid search": 3.0,
        "retrieval": 2.5,
        "ranking": 2.5,
        "ndcg": 3.0,
        "mrr": 3.0,
        "map": 3.0,
        "a/b testing": 2.0,
        "evaluation": 2.0,
        "python": 2.0,
        
        # Secondary
        "lora": 1.5,
        "qlora": 1.5,
        "peft": 1.5,
        "fine-tuning": 1.5,
        "learning to rank": 1.5,
        "xgboost": 1.0,
        "lightgbm": 1.0,
        "distributed systems": 1.0,
        "nlp": 2.0,
        "machine learning": 1.5,
        "deep learning": 1.5,
        "pytorch": 1.5,
        "tensorflow": 1.0,
        "huggingface": 1.5,
        "mlops": 1.5,
    }

    consulting_firms = {
        "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant", 
        "capgemini", "mphasis", "tech mahindra", "mindtree", "l&t", "lnt", "hcl"
    }

    product_companies = {
        "swiggy", "flipkart", "hooli", "pied piper", "stark industries", "wayne enterprises", 
        "paytm", "zomato", "ola", "razorpay", "cred", "amazon", "google", "microsoft", 
        "meta", "netflix", "apple", "adobe", "uber", "salesforce", "atlassian", "nvidia"
    }

    relevant_titles = [
        "machine learning", "ml", "ai", "artificial intelligence", "nlp", "search", 
        "retrieval", "ranking", "data scientist", "data science", "nlp engineer", 
        "applied scientist", "applied science", "backend engineer", "software engineer", 
        "tech lead", "founding engineer"
    ]
    relevant_title_regex = re.compile("|".join([re.escape(t) for t in relevant_titles]), re.IGNORECASE)

    all_scored = []
    honeypots = []
    
    # Accumulate metrics for analytics dashboard
    score_distribution = [0] * 10
    company_type_counts = Counter()
    skills_counter = Counter()
    scatter_data = []
    
    total_candidates = 0

    if candidates_path.endswith(".gz"):
        open_func = lambda p: gzip.open(p, "rt", encoding="utf-8")
    else:
        open_func = lambda p: open(p, "r", encoding="utf-8")

    with open_func(candidates_path) as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            total_candidates += 1
            c_id = c.get("candidate_id")
            
            profile_exp = c.get("profile", {}).get("years_of_experience", 0.0)
            jobs = c.get("career_history", [])
            candidate_skills = c.get("skills", [])
            current_title = c.get("profile", {}).get("current_title", "")
                
            # --- 1. SKILLS SCORING (50%) ---
            candidate_skills = c.get("skills", [])
            individual_skill_scores = []
            for s in candidate_skills:
                name = s.get("name", "").lower()
                proficiency = s.get("proficiency", "beginner")
                duration_months = s.get("duration_months", 0)
                endorsements = s.get("endorsements", 0)
                
                # Skill frequency aggregation for analytical dashboard
                skills_counter[s.get("name")] += 1
                
                # Check target skill weight
                weight = 0.5
                for target_skill, target_w in SKILL_WEIGHTS.items():
                    if target_skill in name:
                        weight = max(weight, target_w)
                        
                # Proficiency multiplier
                prof_mult = 0.2
                if proficiency == "expert":
                    prof_mult = 1.0
                elif proficiency == "advanced":
                    prof_mult = 0.8
                elif proficiency == "intermediate":
                    prof_mult = 0.5
                    
                # Duration factor: 24 months for max credit
                dur_factor = min(duration_months / 24.0, 1.0)
                
                # Endorsements bonus (max +20%)
                endorsement_bonus = 1.0 + min(endorsements / 50.0, 0.2)
                
                skill_val = weight * prof_mult * dur_factor * endorsement_bonus
                individual_skill_scores.append(skill_val)
                
            # Sort descending and apply decay to reward depth
            individual_skill_scores.sort(reverse=True)
            skills_score = 0.0
            decay = 1.0
            for s_val in individual_skill_scores[:8]:
                skills_score += s_val * decay
                decay *= 0.85
                
            # Normalize to 0-10 range
            skills_score = min(skills_score / 6.0 * 10.0, 10.0)
            
            # --- 2. EXPERIENCE SCORING (30%) ---
            exp_score = 0.0
            if 6.0 <= profile_exp <= 8.0:
                exp_score = 10.0
            elif 5.0 <= profile_exp < 6.0:
                exp_score = 8.0
            elif 8.0 < profile_exp <= 9.0:
                exp_score = 8.0
            elif 4.0 <= profile_exp < 5.0:
                exp_score = 5.0
            elif 9.0 < profile_exp <= 12.0:
                exp_score = 5.0
            else:
                exp_score = 2.0
                
            # Title relevance
            title_matches = 0
            total_jobs = len(jobs)
            for job in jobs:
                t = job.get("title", "")
                if relevant_title_regex.search(t):
                    title_matches += 1
            title_factor = (title_matches / total_jobs) if total_jobs > 0 else 0.0
            exp_score = exp_score * (0.5 + 0.5 * title_factor)
            
            # Company type relevance and count metrics
            all_consulting = True
            has_product = False
            for job in jobs:
                comp = job.get("company", "").lower()
                is_c = False
                for c_firm in consulting_firms:
                    if c_firm in comp:
                        is_c = True
                        break
                is_p = False
                for p_comp in product_companies:
                    if p_comp in comp:
                        is_p = True
                        break
                if is_p:
                    has_product = True
                if not is_c:
                    all_consulting = False
                    
            if all_consulting and total_jobs > 0:
                exp_score *= 0.4
                company_type_counts["Consulting"] += 1
                comp_type = "Consulting"
            elif has_product:
                exp_score = min(exp_score * 1.2, 10.0)
                company_type_counts["Product"] += 1
                comp_type = "Product"
            else:
                company_type_counts["Other"] += 1
                comp_type = "Other"
                
            # Job hopping (average tenure)
            if profile_exp > 1.0 and total_jobs > 1:
                avg_tenure = profile_exp / total_jobs
                if avg_tenure < 1.5:
                    exp_score *= 0.8
                    
            # --- 3. EDUCATION SCORING (20%) ---
            edu_score = 3.0
            education_list = c.get("education", [])
            for edu in education_list:
                tier = edu.get("tier", "unknown")
                degree = edu.get("degree", "").lower()
                field = edu.get("field_of_study", "").lower()
                
                # Tier score
                t_score = 3.0
                if tier == "tier_1":
                    t_score = 10.0
                elif tier == "tier_2":
                    t_score = 8.0
                elif tier == "tier_3":
                    t_score = 6.0
                    
                # Field score
                f_mult = 0.5
                if any(term in field for term in ["computer", "data science", "artificial intelligence", "ml", "information technology", "electrical", "mathematics", "statistics"]):
                    f_mult = 1.0
                elif any(term in field for term in ["engineering", "science"]):
                    f_mult = 0.8
                    
                # Degree bonus
                d_bonus = 1.0
                if "phd" in degree or "doctor" in degree:
                    d_bonus = 1.2
                elif "master" in degree or "m.tech" in degree or "m.s" in degree or "mca" in degree:
                    d_bonus = 1.1
                    
                cand_edu_val = t_score * f_mult * d_bonus
                edu_score = max(edu_score, cand_edu_val)
                
            edu_score = min(edu_score, 10.0)
            
            # --- 4. BEHAVIORAL MULTIPLIER ---
            signals = c.get("redrob_signals", {})
            mult = 1.0
            
            # Open to work
            if signals.get("open_to_work_flag"):
                mult *= 1.2
                
            # Recruiter response rate
            resp_rate = signals.get("recruiter_response_rate", 0.5)
            mult *= (0.6 + 1.4 * resp_rate)
            
            # Notice period
            notice = signals.get("notice_period_days", 60)
            if notice <= 30:
                mult *= 1.2
            elif notice <= 60:
                mult *= 1.0
            elif notice <= 90:
                mult *= 0.8
            else:
                mult *= 0.5
                
            # Last active date
            last_active = signals.get("last_active_date", "")
            if last_active:
                try:
                    la_dt = datetime.strptime(last_active, "%Y-%m-%d")
                    days_inactive = (datetime.now() - la_dt).days
                    if days_inactive <= 30:
                        mult *= 1.2
                    elif days_inactive <= 90:
                        mult *= 1.0
                    elif days_inactive <= 180:
                        mult *= 0.8
                    else:
                        mult *= 0.5
                except:
                    pass
                    
            mult = max(0.3, min(2.0, mult))
            
            # --- HONEYPOT DETECTION ---
            # 1. Inverted salary
            sal = c.get("redrob_signals", {}).get("expected_salary_range_inr_lpa", {})
            has_inverted_salary = sal.get("min", 0) > sal.get("max", 0)
            
            # 2. Expert skill with 0 months
            has_expert_zero = any(s.get("proficiency") == "expert" and s.get("duration_months") == 0 for s in candidate_skills)
            
            # 3. Repetitive JDs
            jds = [job.get("description", "").strip() for job in jobs if job.get("description")]
            jds = [jd for jd in jds if len(jd) > 20]
            has_repetitive_jds = False
            if len(jds) > 1:
                counts = Counter(jds)
                if counts.most_common(1)[0][1] > 1:
                    has_repetitive_jds = True
                    
            # 4. Keyword stuffing
            is_non_tech = bool(non_tech_regex.search(current_title))
            tech_skills_count = 0
            if is_non_tech:
                skills_list = [s.get("name", "") for s in candidate_skills]
                tech_skills_count = sum(1 for s in skills_list if tech_skills_regex.search(s))
            has_keyword_stuffing = is_non_tech and tech_skills_count >= 10
            
            # 5. Timeline checks
            total_stated_months = 0
            has_mismatch = False
            for job in jobs:
                start_str = job.get("start_date")
                end_str = job.get("end_date")
                stated_dur = job.get("duration_months", 0)
                total_stated_months += stated_dur
                if start_str:
                    try:
                        s_dt = datetime.strptime(start_str, "%Y-%m-%d")
                        e_dt = datetime.strptime(end_str, "%Y-%m-%d") if end_str else datetime.now()
                        diff_months = (e_dt.year - s_dt.year) * 12 + (e_dt.month - s_dt.month)
                        if abs(stated_dur - diff_months) > 2:
                            has_mismatch = True
                    except:
                        pass
            stated_years = total_stated_months / 12.0
            has_unreasonable_exp = abs(profile_exp - stated_years) > 1.0
            
            # Composite honeypot condition
            is_honeypot = False
            honeypot_issue = ""
            if (has_expert_zero or has_mismatch or has_unreasonable_exp or has_keyword_stuffing) and (has_inverted_salary or has_repetitive_jds):
                is_honeypot = True
                if has_expert_zero:
                    honeypot_issue = "Expert skills with 0 months experience"
                elif has_keyword_stuffing:
                    honeypot_issue = "Keyword stuffing on non-tech title"
                elif has_mismatch or has_unreasonable_exp:
                    honeypot_issue = "Timeline inconsistency in career duration"
                else:
                    honeypot_issue = "Inconsistent profile metrics"

            # --- COMPOSITE SCORE ---
            base_score = 0.5 * skills_score + 0.3 * exp_score + 0.2 * edu_score
            final_score = base_score * mult
            display_score = 0.0 if is_honeypot else final_score
            
            # Accumulate analytics data (only for valid candidates)
            if not is_honeypot:
                bucket = min(int(final_score), 9)
                score_distribution[bucket] += 1
                
                # Scatter plot sample aggregation (add a fraction of data to keep json size small)
                if total_candidates % 100 == 0:
                    scatter_data.append({
                        "name": c.get("profile", {}).get("anonymized_name", "Candidate"),
                        "exp": profile_exp,
                        "score": round(final_score, 2),
                        "company_type": comp_type,
                        "skills_count": len(candidate_skills)
                    })
            
            # --- REASONING GENERATION ---
            if is_honeypot:
                reasoning = f"Honeypot Profile Detected: {honeypot_issue}. Excluded from ranking."
            else:
                named_skills = [s.get("name") for s in candidate_skills if any(t in s.get("name").lower() for t in ["embeddings", "vector", "search", "retrieval", "pytorch", "llm", "ndcg", "mrr"])]
                skills_str = ", ".join(named_skills[:3]) if named_skills else "applied ML"
                current_comp = c.get("profile", {}).get("current_company", "a top company")
                
                if final_score >= 8.5:
                    reasoning = f"Exceptional candidate with {profile_exp:.1f} years experience in ML; shipped {skills_str} systems; high engagement and availability."
                elif final_score >= 7.0:
                    reasoning = f"Strong technical profile showing {profile_exp:.1f} years of experience with {skills_str}; background includes work at {current_comp}."
                elif final_score >= 5.0:
                    reasoning = f"Solid background with {profile_exp:.1f} years in software/ML; has good skills in {skills_str} but notice period or activity slightly limits fit."
                else:
                    reasoning = f"Adjacent skills in {skills_str} and {profile_exp:.1f} years of experience, but overall matching is weaker for this specific role."
                
            candidate_entry = {
                "candidate_id": c_id,
                "name": c.get("profile", {}).get("anonymized_name", "Candidate"),
                "headline": c.get("profile", {}).get("headline", ""),
                "years_of_experience": profile_exp,
                "current_company": c.get("profile", {}).get("current_company", ""),
                "current_title": current_title,
                "location": c.get("profile", {}).get("location", ""),
                "score": round(display_score, 3),
                "original_score": round(final_score, 3),
                "is_honeypot": is_honeypot,
                "honeypot_issue": honeypot_issue,
                
                # Rule flags for settings config
                "has_expert_zero": has_expert_zero,
                "has_keyword_stuffing": has_keyword_stuffing,
                "has_mismatch": has_mismatch or has_unreasonable_exp,
                "has_inverted_salary": has_inverted_salary,
                "has_repetitive_jds": has_repetitive_jds,
                
                "skills_score": round(skills_score, 2),
                "exp_score": round(exp_score, 2),
                "edu_score": round(edu_score, 2),
                "multiplier": round(mult, 2),
                "skills": candidate_skills[:8],
                "career_history": [{
                    "company": j.get("company"),
                    "title": j.get("title"),
                    "start_date": j.get("start_date"),
                    "end_date": j.get("end_date"),
                    "duration_months": j.get("duration_months"),
                    "description": j.get("description", "")[:100] + "..." if j.get("description") else ""
                } for j in jobs],
                "education": education_list,
                "redrob_signals": {
                    "open_to_work_flag": signals.get("open_to_work_flag"),
                    "recruiter_response_rate": signals.get("recruiter_response_rate"),
                    "notice_period_days": signals.get("notice_period_days"),
                    "last_active_date": signals.get("last_active_date")
                },
                "reasoning": reasoning
            }
            
            all_scored.append(candidate_entry)
            if is_honeypot:
                honeypots.append(candidate_entry)

    # Sort scored candidates by score descending, and deterministically by candidate_id ascending on ties
    all_scored.sort(key=lambda x: (-x["score"], x["candidate_id"]))
    
    # Save the top 100 to CSV
    csv_rows = ["candidate_id,rank,score,reasoning"]
    for idx, sc in enumerate(all_scored[:100]):
        # escape quotes in reasoning
        reasoning_escaped = sc["reasoning"].replace('"', '""')
        csv_rows.append(f'{sc["candidate_id"]},{idx+1},{sc["score"]:.3f},"{reasoning_escaped}"')
        
    with open(csv_out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_rows) + "\n")
        
    # Precompute summary details for the dashboard to keep it lightweight
    top_skills_list = [{"skill": s, "count": count} for s, count in skills_counter.most_common(12)]
    
    # Radar avg scores for top 100 vs all candidates
    avg_top_100 = {
        "skills": sum(x["skills_score"] for x in all_scored[:100]) / 100,
        "exp": sum(x["exp_score"] for x in all_scored[:100]) / 100,
        "edu": sum(x["edu_score"] for x in all_scored[:100]) / 100,
        "multiplier": sum(x["multiplier"] for x in all_scored[:100]) / 100
    }
    
    # Samples for averages (exclude honeypots from avg scores of all candidates)
    valid_candidates = [x for x in all_scored if not x["is_honeypot"]]
    avg_all = {
        "skills": sum(x["skills_score"] for x in valid_candidates) / len(valid_candidates),
        "exp": sum(x["exp_score"] for x in valid_candidates) / len(valid_candidates),
        "edu": sum(x["edu_score"] for x in valid_candidates) / len(valid_candidates),
        "multiplier": sum(x["multiplier"] for x in valid_candidates) / len(valid_candidates)
    }
    
    dashboard_data = {
        "metadata": {
            "total_candidates": total_candidates,
            "honeypots_detected": len(honeypots),
            "average_score": round(sum(x["score"] for x in valid_candidates) / len(valid_candidates), 2),
            "top_100_ready": 100
        },
        "score_distribution": score_distribution,
        "company_type_counts": dict(company_type_counts),
        "top_skills": top_skills_list,
        "scatter_data": scatter_data,
        "radar_data": {
            "top_100": avg_top_100,
            "all": avg_all
        },
        "top_candidates": all_scored[:200], # Provide top 200 candidates
        "honeypots": honeypots[:100] # Provide detected honeypots (there are ~80)
    }
    
    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2)
        
    print(f"Ranking and data generation completed in {time.time() - start_time:.2f} seconds.")
    print(f"Submission written to {csv_out_path}")
    print(f"Dashboard data written to {json_out_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Redrob AI - Candidate Ranking & Discovery Engine")
    parser.add_argument("--candidates", type=str, default="candidates.jsonl", help="Path to candidates jsonl dataset")
    parser.add_argument("--out", type=str, default="submission.csv", help="Path to write ranked submission.csv")
    args = parser.parse_args()

    # Determine out directory and ensure dashboard directory exists in the same location
    out_dir = os.path.dirname(os.path.abspath(args.out))
    dashboard_dir = os.path.join(out_dir, "dashboard")
    os.makedirs(dashboard_dir, exist_ok=True)
    json_out = os.path.join(dashboard_dir, "dashboard_data.json")
    
    run_ranking(args.candidates, args.out, json_out)
