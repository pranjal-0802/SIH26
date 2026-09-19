from typing import Dict, Any, Tuple

# Explicit life-safety crisis keywords that trigger immediate algorithmic bypass
CRISIS_KEYWORDS = [
    "suicide", "kill myself", "end it all", "hang myself", 
    "shoot myself", "hopeless", "can't live", "want to die", 
    "no reason to live", "ending my life", "self harm"
]

def check_crisis_indicators(reflection_text: str, phq4_score: float) -> Tuple[bool, str]:
    """
    Checks for acute life-safety risk or active self-harm signals.
    """
    if not reflection_text and phq4_score < 11.0:
        return False, ""
    
    text_lower = (reflection_text or "").lower()
    for kw in CRISIS_KEYWORDS:
        if kw in text_lower:
            return True, f"Explicit self-harm / crisis keyword detected: '{kw}'."
            
    # Extreme PHQ-4 score (11-12) coupled with acute negative tone
    if phq4_score >= 11.0 and any(w in text_lower for w in ["cannot go on", "breakdown", "finished", "pain"]):
        return True, "Severe depressive crisis score (PHQ-4 >= 11) with acute distress reflection."
        
    return False, ""

def calculate_stress_risk(
    phq4_score: float,            # 0 to 12
    mood_score: float,            # 1 to 10 (higher is happier)
    sleep_hours: float,           # e.g. 4.0 to 8.0
    stress_rating: float,         # 1 to 10 (higher is more stressed)
    days_since_leave: int,        # e.g. 0 to 300
    denied_leaves: int,           # e.g. 0 to 5
    deployment_hardship: float,   # 1.0 to 5.0 (high altitude, CI ops)
    night_shifts_ratio: float,    # 0.0 to 1.0
    sentiment_polarity: float = 0.0, # -1.0 to +1.0
    reflection_text: str = ""     # Raw reflection note for crisis screening
) -> Dict[str, Any]:
    """
    Explainable Behavioral Stress & Burnout Risk Model.
    Transparently aggregates multi-source operational and clinical stressors.
    Enforces immediate CRISIS HARD-OVERRIDE for life-safety self-harm signals.
    """
    # 0. CHECK CRISIS HARD-OVERRIDE FIRST
    is_crisis, crisis_reason = check_crisis_indicators(reflection_text, phq4_score)
    if is_crisis:
        return {
            "composite_risk_score": 1.0,
            "risk_percentage": 100.0,
            "risk_tier": "CRITICAL",
            "is_crisis_override": True,
            "crisis_reason": crisis_reason,
            "operational_subscore": 1.0,
            "psychometric_subscore": 1.0,
            "attributions": {
                "CRITICAL LIFE-SAFETY OVERRIDE": 100.0
            }
        }

    # 1. Operational Hardship Components (Normalized 0.0 to 1.0)
    norm_leave_deficit = min(1.0, max(0.0, (days_since_leave - 60) / 180.0))
    norm_denied_leaves = min(1.0, denied_leaves / 3.0)
    norm_hardship = min(1.0, max(0.0, (deployment_hardship - 1.0) / 4.0))
    norm_night_shifts = min(1.0, max(0.0, night_shifts_ratio))

    op_subscore = (
        0.35 * norm_leave_deficit +
        0.30 * norm_denied_leaves +
        0.20 * norm_hardship +
        0.15 * norm_night_shifts
    )

    # 2. Psychometric & Self-Report Components (Normalized 0.0 to 1.0)
    norm_phq4 = min(1.0, max(0.0, phq4_score / 12.0))
    norm_mood_distress = min(1.0, max(0.0, (10.0 - mood_score) / 9.0))
    norm_sleep_deficit = min(1.0, max(0.0, (7.5 - sleep_hours) / 4.5))
    norm_stress = min(1.0, max(0.0, (stress_rating - 1.0) / 9.0))
    norm_sentiment = min(1.0, max(0.0, (-sentiment_polarity + 0.2) / 1.2))

    psy_subscore = (
        0.30 * norm_phq4 +
        0.25 * norm_sleep_deficit +
        0.20 * norm_stress +
        0.15 * norm_mood_distress +
        0.10 * norm_sentiment
    )

    # 3. Composite Risk Calculation (45% Operational HR + 55% Psych/Sleep)
    composite_risk = (0.45 * op_subscore) + (0.55 * psy_subscore)
    composite_risk = round(min(1.0, max(0.0, composite_risk)), 4)

    # 4. Feature Attributions for Explainability
    raw_weights = {
        "Leave Deficit Duration": 0.45 * 0.35 * norm_leave_deficit,
        "Denied Leave Applications": 0.45 * 0.30 * norm_denied_leaves,
        "Deployment Hardship Index": 0.45 * 0.20 * norm_hardship,
        "Night Shift Disruption": 0.45 * 0.15 * norm_night_shifts,
        "PHQ-4 Screening Score": 0.55 * 0.30 * norm_phq4,
        "Sleep Deprivation": 0.55 * 0.25 * norm_sleep_deficit,
        "Self-Reported Tension": 0.55 * 0.20 * norm_stress,
        "Mood & Sentiment Fatigue": 0.55 * 0.25 * (norm_mood_distress + norm_sentiment) / 2.0
    }

    total_weight = sum(raw_weights.values())
    attributions = {}
    if total_weight > 0.001:
        for k, v in raw_weights.items():
            pct = round((v / total_weight) * 100.0, 1)
            if pct > 0.0:
                attributions[k] = pct
    else:
        attributions = {"Baseline Equilibrium": 100.0}

    # 5. Risk Tier Assignment
    if composite_risk >= 0.75:
        tier = "CRITICAL"
    elif composite_risk >= 0.55:
        tier = "ELEVATED"
    elif composite_risk >= 0.35:
        tier = "MODERATE"
    else:
        tier = "LOW"

    return {
        "composite_risk_score": composite_risk,
        "risk_percentage": round(composite_risk * 100.0, 1),
        "risk_tier": tier,
        "is_crisis_override": False,
        "crisis_reason": None,
        "operational_subscore": round(op_subscore, 3),
        "psychometric_subscore": round(psy_subscore, 3),
        "attributions": attributions
    }
