import os
import json
import threading
from typing import Any, Dict, List, Optional, Tuple

import requests

try:
    # Optional local LLM offline support
    from gpt4all import GPT4All  # type: ignore
except Exception:  # pragma: no cover - optional
    GPT4All = None  # type: ignore

from kivy.resources import resource_find


def load_local_knowledge_base() -> List[Dict[str, Any]]:
    kb_rel_path = os.path.join("data", "local_knowledge_base.json")
    kb_path = resource_find(kb_rel_path) or kb_rel_path
    if not os.path.exists(kb_path):
        return []
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def load_user_knowledge_base(user_kb_path: Optional[str]) -> List[Dict[str, Any]]:
    if not user_kb_path:
        return []
    if not os.path.exists(user_kb_path):
        return []
    try:
        with open(user_kb_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def jaccard_similarity(a: str, b: str) -> float:
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    inter = sa.intersection(sb)
    union = sa.union(sb)
    return len(inter) / max(1, len(union))


class LocalKnowledgeBase:
    def __init__(self, user_kb_path: Optional[str] = None) -> None:
        self.user_kb_path = user_kb_path
        default_qa = load_local_knowledge_base()
        user_qa = load_user_knowledge_base(user_kb_path)
        self.qa_pairs = default_qa + user_qa
        self.lock = threading.Lock()

    def search(self, question: str) -> Optional[str]:
        best_score = 0.0
        best_answer: Optional[str] = None
        for item in self.qa_pairs:
            score = jaccard_similarity(question, item.get("q", ""))
            if score > best_score:
                best_score = score
                best_answer = item.get("a")
        if best_score >= 0.2 and best_answer:
            return best_answer
        return None

    def learn(self, question: str, answer: str) -> None:
        with self.lock:
            self.qa_pairs.append({"q": question, "a": answer})
            if not self.user_kb_path:
                return
            try:
                os.makedirs(os.path.dirname(self.user_kb_path), exist_ok=True)
                # Write only user kb to keep packaged defaults intact
                # Filter only pairs not in defaults by naive uniqueness on (q,a)
                with open(self.user_kb_path, "w", encoding="utf-8") as f:
                    json.dump(self.qa_pairs, f, indent=2, ensure_ascii=False)
            except Exception:
                pass


class LocalAIAgent:
    def __init__(self, persona_prompt: str, model_name: Optional[str] = None, kb_path: Optional[str] = None) -> None:
        self.persona_prompt = persona_prompt
        self.kb = LocalKnowledgeBase(user_kb_path=kb_path)
        self.gpt4all_model_name = model_name
        self._gpt4all = None
        if GPT4All and model_name:
            try:
                self._gpt4all = GPT4All(model_name)
            except Exception:
                self._gpt4all = None

    def answer(self, question: str, chat_history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, Dict[str, Any]]:
        # First try knowledge base retrieval
        kb_answer = self.kb.search(question)
        if kb_answer:
            styled = f"{self.persona_prompt}\n\n{kb_answer}"
            return styled, {"provider": "local_kb"}
        # Try GPT4All if available
        if self._gpt4all:
            try:
                prompt = f"{self.persona_prompt}\n\nUser: {question}\nAssistant:"
                response = self._gpt4all.generate(prompt, max_tokens=256, temp=0.4)
                if response:
                    return response.strip(), {"provider": "gpt4all", "model": self.gpt4all_model_name}
            except Exception:
                pass
        # Fallback canned response for offline
        fallback = (
            "I am currently operating in offline mode. Based on my onboard knowledge, here are best practices: "
            "1) Keep OS and apps updated. 2) Use a password manager and MFA. 3) Avoid sideloading unknown APKs. "
            "4) Back up regularly. 5) Use device encryption. Ask again when online for deeper analysis."
        )
        styled = f"{self.persona_prompt}\n\n{fallback}"
        return styled, {"provider": "local_fallback"}


class OnlineAIAgent:
    def __init__(self, persona_prompt: str) -> None:
        self.persona_prompt = persona_prompt

    def answer_with_openai(self, api_key: str, question: str, model: str = "gpt-3.5-turbo") -> Tuple[str, Dict[str, Any]]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        messages = [
            {"role": "system", "content": self.persona_prompt},
            {"role": "user", "content": question},
        ]
        payload = {"model": model, "messages": messages, "temperature": 0.2}
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        return content, {"provider": "openai", "model": model}

    def answer_with_hf(self, api_key: str, question: str, model: str = "meta-llama/Meta-Llama-3-8B-Instruct") -> Tuple[str, Dict[str, Any]]:
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "inputs": f"{self.persona_prompt}\n\nUser: {question}\nAssistant:",
            "parameters": {"max_new_tokens": 256, "temperature": 0.2, "return_full_text": False},
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            text = data[0].get("generated_text", "").strip()
        else:
            text = (data.get("generated_text") or "").strip()
        return text, {"provider": "huggingface", "model": model}

    # Placeholders for extended enterprise providers
    def answer_with_ibm_watson(self, question: str) -> Tuple[str, Dict[str, Any]]:
        return (
            "IBM watsonx integration can be enabled here. For now, I can provide guidance using my current engines.",
            {"provider": "ibm_watson_stub"},
        )

    def answer_with_ms_copilot(self, question: str) -> Tuple[str, Dict[str, Any]]:
        return (
            "Microsoft Copilot connector is available for enterprise deployments; contact your admin to link it.",
            {"provider": "ms_copilot_stub"},
        )