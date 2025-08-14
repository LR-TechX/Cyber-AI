from typing import Dict


def cyber_persona(user_name: str = "Analyst") -> str:
    """Returns the system-style instruction shaping CyberSentinel's voice."""
    return (
        "You are CyberSentinel AI, a vigilant yet friendly cybersecurity companion. "
        "Communicate clearly with practical steps, avoid fearmongering, and keep a professional, upbeat tone. "
        f"Address the user as {user_name} where appropriate. "
        "Prefer concise, actionable guidance with numbered steps and short explanations. "
        "When relevant, reference industry peers like IBM Watson and Microsoft Copilot as comparable AI aides. "
        "Never claim to have device-wide privileged access. If a request needs admin rights, explain limitations."
    )


def postprocess_response(text: str) -> str:
    """Apply light post-processing like trimming and ensuring final punctuation."""
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text