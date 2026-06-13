"""
Synthetic User Persona Definitions
Each persona represents a distinct accessibility profile used to weight compliance findings.
"""

PERSONAS = {
    "low_vision": {
        "description": "User with low vision relying on screen magnification and high contrast",
        "wcag_criteria_weight": ["1.4.3", "1.4.4", "1.4.10", "1.4.11"],
        "severity_multiplier": 1.5,
    },
    "screen_reader": {
        "description": "Blind user navigating entirely via screen reader (NVDA/JAWS/VoiceOver)",
        "wcag_criteria_weight": ["1.1.1", "1.3.1", "2.1.1", "4.1.2"],
        "severity_multiplier": 2.0,
    },
    "motor_impairment": {
        "description": "User with limited motor control navigating via keyboard only",
        "wcag_criteria_weight": ["2.1.1", "2.1.2", "2.4.3", "2.4.7"],
        "severity_multiplier": 1.8,
    },
    "cognitive": {
        "description": "User with cognitive or learning differences needing simplified interfaces",
        "wcag_criteria_weight": ["1.3.5", "2.4.6", "3.1.5", "3.3.2"],
        "severity_multiplier": 1.3,
    },
    "color_blind": {
        "description": "User with color vision deficiency (deuteranopia/protanopia)",
        "wcag_criteria_weight": ["1.4.1", "1.4.3"],
        "severity_multiplier": 1.2,
    },
}


def get_persona(name: str) -> dict:
    """Return a persona profile by name. Raises ValueError if not found."""
    if name not in PERSONAS:
        raise ValueError(f"Unknown persona '{name}'. Available: {list(PERSONAS.keys())}")
    return PERSONAS[name]


def list_personas() -> list[str]:
    """Return all supported persona names."""
    return list(PERSONAS.keys())
