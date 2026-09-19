from typing import Dict, Any, List

def generate_explainability_summary(evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produces transparent, non-black-box rationale and tailored welfare recommendations.
    Directly counteracts black-box stigmatization concerns in armed forces.
    """
    pseudo_id = evaluation.get("pseudo_id", "UNKNOWN")
    archetype = evaluation.get("signal_archetype", "BASELINE")
    attributions = evaluation.get("attributions", {})
    op_subscore = evaluation.get("operational_subscore", 0.0)
    psy_subscore = evaluation.get("psychometric_subscore", 0.0)
    
    # Sort top contributors
    sorted_factors = sorted(attributions.items(), key=lambda x: x[1], reverse=True)
    top_drivers = [f"{factor}: {pct}% contribution" for factor, pct in sorted_factors[:3]]

    recommendations: List[str] = []
    
    # Targeted operational recommendations
    if any("Leave" in k for k, _ in sorted_factors[:2]):
        recommendations.append(
            "Priority Leave Sanction: Grant 10-14 days Rest & Recuperation (R&R) to relieve extended deployment fatigue."
        )
    if any("Sleep" in k or "Night Shift" in k for k, _ in sorted_factors[:2]):
        recommendations.append(
            "Duty Shift Rebalancing: Rotate personnel off consecutive night sentry shifts for 7 days to restore circadian sleep rhythm."
        )
    if any("PHQ" in k or "Tension" in k for k, _ in sorted_factors[:2]):
        recommendations.append(
            "Confidential Counseling: Initiate supportive, non-stigmatizing session with the Unit Medical/Welfare Officer."
        )

    # Strategic archetype recommendations
    if archetype == "STIGMA_MASKED_DISTRESS":
        recommendations.append(
            "Peer-Buddy Assignment: Discrete buddy support check without threatening weapon qualification or operational standing."
        )
    elif archetype == "NOISY_UNSUBSTANTIATED":
        recommendations.append(
            "Routine Monitoring: Check-in scheduled during standard weekly welfare roll call; no emergency escalation indicated."
        )

    if not recommendations:
        recommendations.append("Maintain standard unit wellness monitoring and periodic voluntary check-ins.")

    plain_summary = (
        f"Alert for {pseudo_id} is evaluated with {evaluation.get('p_true_distress', 0.0)*100:.0f}% confidence of genuine distress. "
        f"Primary drivers: {'; '.join(top_drivers)}. "
        f"Strategic Classification: {evaluation.get('strategic_rationale', '')}"
    )

    return {
        "pseudo_id": pseudo_id,
        "signal_archetype": archetype,
        "plain_language_summary": plain_summary,
        "top_drivers": top_drivers,
        "recommended_interventions": recommendations
    }

