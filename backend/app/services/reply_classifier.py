"""
Reply Classifier V1: deterministic keyword-based classification.
No AI calls — human-in-the-loop sprint only.
"""

from __future__ import annotations

_RULES: list[tuple[list[str], str, str]] = [
    (
        ["price", "expensive", "cost", "too much", "afford", "cheap", "budget"],
        "price",
        "I understand. Many customers feel the same at first, but we often have financing or flexible options available. Would you like me to walk you through them?",
    ),
    (
        ["later", "not ready", "maybe next month", "not yet", "wait", "next week", "next year", "some time"],
        "timing",
        "Totally understandable. When would be a better time for us to follow up with you?",
    ),
    (
        ["yes", "interested", "tell me more", "sounds good", "i'm in", "im in", "sure", "absolutely", "definitely", "sign me up", "let's do it", "lets do it"],
        "interested",
        "Great! I'd be happy to help. Would you prefer a quick call or more details by message?",
    ),
    (
        ["no thanks", "stop", "not interested", "unsubscribe", "remove me", "do not contact", "dont contact", "leave me alone", "opt out"],
        "not_interested",
        "Understood. If things change later feel free to reach out.",
    ),
    (
        ["help", "human", "agent", "person", "real person", "talk to someone", "speak to", "representative", "manager"],
        "human_needed",
        "Of course! Let me connect you with a team member right away.",
    ),
    (
        ["info", "information", "more details", "brochure", "details", "how does", "what is", "explain", "question"],
        "info",
        "Happy to share more information! What specifically would you like to know?",
    ),
]


def classify_reply(text: str) -> dict:
    """
    Classify a lead reply using keyword heuristics.

    Returns:
        {
            "classification": str,   # interested|price|timing|info|not_interested|human_needed|unknown
            "suggested_response": str
        }
    """
    lowered = text.lower()

    for keywords, classification, suggested_response in _RULES:
        for kw in keywords:
            if kw in lowered:
                return {
                    "classification": classification,
                    "suggested_response": suggested_response,
                }

    return {
        "classification": "unknown",
        "suggested_response": "Thanks for your message. Let me connect you with someone who can help.",
    }
