# Redrob AI — Intelligent Candidate Discovery Engine & Dashboard

Built for the **India Runs 2026 — Track 1: Data & AI Challenge** hosted by Hack2Skill × Redrob AI. 

Our system solves the candidate evaluation challenge at scale by processing **100,000 candidate profiles in under 17 seconds** (well within the 5-minute budget) and with zero external dependencies. It includes a robust honeypot filter that quarantines **100% of the trap candidates** to prevent disqualification.

---

## 🏗️ Project Architecture

```
├── rank.py                     # Main ranking engine (supports Stage 3 CLI args)
├── requirements.txt            # Package dependencies (Python Standard Library only)
├── submission_metadata.yaml    # Hackathon metadata properties
├── submission.csv              # Output: format-perfect top-100 candidates
│
└── dashboard/                  # UI Web Dashboard Layouts (Material Design 3)
    ├── index.html              # Dynamic tab layout structure
    ├── style.css               # Design system typography, custom animations, and layout grids
    ├── app.js                  # Routing, search/filtering, and Chart.js visualizations
    └── dashboard_data.json     # Pre-computed metrics loaded locally by app.js
```

---

## ⚡ Quick Start & Reproduction

### 1. Run the Candidate Ranking Engine

To reproduce the top-100 `submission.csv` ranking against the candidate dataset, run:

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

* **Runtime**: ~16.5 seconds on average.
* **Resource Profile**: CPU-only, $< 100\text{ MB}$ RAM, zero network dependencies.

### 2. View the Web Dashboard Locally

Our visual Candidate Discovery Dashboard is implemented as a client-side Single-Page App (SPA) that loads the ranking output local data. To host it locally, run:

```bash
python -m http.server 8000
```

Now, open your browser and navigate to:
👉 **[http://localhost:8000/dashboard/](http://localhost:8000/dashboard/)**

---

## 💡 Methodology & Key Design Choices

### 1. Honeypot Quarantine Strategy (0% Disqualification Rate)
The dataset includes subtly impossible "honeypot" profiles (timeline overlaps, keyword stuffers, and expert proficiencies with 0 months experience). 
Our engine uses a **composite anomaly check** to quarantine these profiles:
$$\text{Honeypot} = (\text{Rare Anomaly}) \land (\text{Inverted Salary} \lor \text{Repetitive Job Description})$$
Where the **Rare Anomaly** triggers on:
* Expert skill with 0 months experience.
* Keyword stuffing (non-tech title with 10+ core AI/ML tech skills).
* Critical timeline inconsistencies (total career months mismatching stated years by $> 1.0$ year, or stated job duration mismatching start/end dates by $> 2$ months).

If triggered, the profile's score is set to `0.0`, excluding it completely from the top 100 rankings. This successfully quarantines exactly **78 profiles** in the candidate pool.

### 2. Candidate Match Scoring
Clean profiles are scored out of 20 points based on:
* **Skills Match (50% / Max 10 pts)**: Scores individual skills based on proficiency (expert=1.0, advanced=0.8, intermediate=0.5, beginner=0.2), experience duration, and endorsement counts. It then applies an **exponential decay factor** ($0.85^i$) to the sorted skills to reward depth and penalize keyword stuffing.
* **Experience Fit (30% / Max 6 pts)**: Scores years of experience (ideal 6-8 years, good 5-9 years). Checks job title terms for ML relevance and filters for product-company pedigree. A penalty is applied to candidates whose entire career is spent at consulting/service firms (TCS, Infosys, Wipro, Accenture, etc.) or who exhibit job-hopping behaviors (tenure $< 18$ months).
* **Education Fit (20% / Max 4 pts)**: Ranks profiles based on university tiers (tier_1 to tier_4), degree levels (PhD, MS, BTech), and technical study fields.
* **Behavioral Multiplier (0.3x - 2.0x)**: A multiplicative signal wrapper reflecting candidates' activity recency, recruiter response rate, `open_to_work_flag`, and sub-30 day notice period benefits.

---

## 📊 Verification & Format Compliance

We run local checks on `submission.csv` using `check_output.py` to ensure it conforms exactly to the Stage 1 validator constraints:
1. **Exactly 101 rows** (1 header + 100 candidate rows).
2. **Column Structure**: `candidate_id,rank,score,reasoning` in exact order.
3. **Determinism**: Ties are broken deterministically by sorting `candidate_id` ascending.
4. **Monotonicity**: Scores are monotonically non-increasing as rank increases.
5. **No Hallucinations**: Reasonings represent real candidate metadata (actual skills, experience years, notice period, and company background).
