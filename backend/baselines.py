"""Stateless guardrail baselines (UNTESTED here: need GPU / gated weights / an LLM key).

Each exposes the detector interface (``name``, ``use_context``, ``score(text, hop)`` -> trust in [0, 1])
so scripts/benchmark.py can run them on exactly the same events as MAPIS.
"""

from __future__ import annotations

from backend.core.context import action_text


def _message_text(hop: dict) -> str:
    return " ".join(str(x) for x in (hop.get("content"), hop.get("tool_response"), action_text(hop)) if x)


class LlamaGuardBaseline:
    """Meta Llama Guard 3 (needs `hf auth login` and access to meta-llama/Llama-Guard-3-1B)."""

    name, use_context = "llama-guard-3", False

    def __init__(self, model_id: str = "meta-llama/Llama-Guard-3-1B"):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        try:  # `dtype` on new transformers, `torch_dtype` on old ones; no accelerate needed
            model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype)
        except TypeError:
            model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=dtype)
        self.model = model.to(self.device).eval()

    def score_chunks(self, texts: list[str], hop: dict) -> tuple[float, int]:
        chat = [{"role": "user", "content": [{"type": "text", "text": _message_text(hop)[:6000]}]}]
        enc = self.tokenizer.apply_chat_template(chat, return_tensors="pt", return_dict=True)
        input_ids = enc["input_ids"].to(self.device)
        with self.torch.inference_mode():
            out = self.model.generate(input_ids, max_new_tokens=8, do_sample=False, pad_token_id=self.tokenizer.eos_token_id)
        verdict = self.tokenizer.decode(out[0][input_ids.shape[-1]:], skip_special_tokens=True).strip().lower()
        return (0.0 if verdict.startswith("unsafe") else 1.0), 0


class NemoBaseline:
    """NVIDIA NeMo Guardrails with a self-check input rail (needs `pip install nemoguardrails` and OPENAI_API_KEY)."""

    name, use_context = "nemo-guardrails", False

    def __init__(self, config_dir: str = "configs/nemo"):
        from nemoguardrails import LLMRails, RailsConfig

        self.rails = LLMRails(RailsConfig.from_path(config_dir))

    def score_chunks(self, texts: list[str], hop: dict) -> tuple[float, int]:
        reply = self.rails.generate(messages=[{"role": "user", "content": _message_text(hop)[:6000]}])
        return (0.0 if "can't respond" in reply["content"].lower() or "cannot respond" in reply["content"].lower() else 1.0), 0
