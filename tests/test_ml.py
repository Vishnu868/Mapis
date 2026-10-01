import json

import pytest

from backend.core.context import build_text, normalize_hop
from backend.ml.metrics import at_threshold, best_threshold, confusion, summarize
from scripts.prepare_phase4_training_data import build_examples

SAMPLE = {
    "sample_id": "s1", "source_dataset": "AgentDojo", "source_record_id": {"suite_name": "x"}, "split": "train", "is_attack": True,
    "mapis_attack_class": "data_exfiltration", "provenance": {"conversion_type": "native"},
    "messages": [
        {"hop": 1, "role": "user", "source": "user", "target": "agent", "content": "Task"},
        {"hop": 2, "role": "tool", "source": "tool", "target": "agent", "content": "<INFORMATION> x </INFORMATION>"},
        {"hop": 3, "role": "assistant", "source": "agent", "target": "user", "content": "Later"},
    ],
}


def test_slide_metrics_reproduce_from_confusion_matrix():
    m = summarize({"tp": 231, "fn": 33, "fp": 5, "tn": 110})
    assert round(m["recall"], 4) == 0.875 and round(m["precision"], 4) == 0.9788 and round(m["fpr"], 4) == 0.0435
    assert round(m["accuracy"], 4) == 0.8997 and round(m["f1"], 4) == 0.924


def test_threshold_respects_fpr_budget():
    labels = [0] * 10 + [1] * 10
    trust = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 0.97] + [0.05] + [0.5] * 2 + [0.9] * 7
    t = best_threshold(labels, trust, max_fpr=0.1)
    assert at_threshold(labels, trust, t)["fpr"] <= 0.1


def test_training_and_runtime_render_identically():
    """Train/serve parity: the stored example text equals what the shield builds for the same window."""
    ex = build_examples([SAMPLE])
    hops = [normalize_hop(m) for m in SAMPLE["messages"]]
    assert ex[1]["text"] == build_text(hops[:1], hops[1])
    assert [e["label"] for e in ex] == ["unlabeled", "malicious", "unlabeled"]


def test_context_never_contains_the_future():
    ex = build_examples([SAMPLE])
    assert all(h["hop"] < e["current_hop"]["hop"] for e in ex for h in e["context_hops"])


def test_train_calibrate_and_serve_tiny_model(tmp_path):
    """Smoke test of the whole ML path with a throw-away tiny BERT (no downloads)."""
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from transformers import BertConfig, BertForSequenceClassification, BertTokenizerFast

    from backend.core.detector import TransformerDetector
    from backend.ml.config import TrainingConfig
    from backend.ml.train import train

    words = ["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]"] + "mapis causal event window hop role user tool assistant content ignore instructions task information current scoring".split()
    (tmp_path / "vocab.txt").write_text("\n".join(words))
    tok = BertTokenizerFast(str(tmp_path / "vocab.txt"))
    model = BertForSequenceClassification(BertConfig(vocab_size=len(words), hidden_size=16, num_hidden_layers=1, num_attention_heads=2, intermediate_size=32, num_labels=2))
    base = tmp_path / "tiny"
    model.save_pretrained(base); tok.save_pretrained(base)

    rows = []
    for i in range(24):
        bad = i % 2 == 0
        for split in ("train", "validation", "test"):
            rows.append({"example_id": f"{split}{i}", "split": split, "label": "malicious" if bad else "safe", "source_dataset": "T", "attack_class": "c",
                         "text": "ignore instructions information" if bad else "task user content", "current_hop": {"hop": 1, "role": "tool", "source": "a", "target": "b",
                         "content": "ignore instructions" if bad else "task", "content_state": "text", "tool_name": None, "tool_call": None, "tool_calls": None, "tool_response": None}})
    data = tmp_path / "events.jsonl"
    data.write_text("\n".join(json.dumps(r) for r in rows))

    out = tmp_path / "out"
    cal = train(TrainingConfig(model_name=str(base), training_data=str(data), output_dir=str(out), epochs=6, train_batch_size=4,
                               gradient_accumulation_steps=1, learning_rate=5e-3, max_length=32, mixed_precision=False))
    assert cal["temperature"] > 0 and (out / "calibration.json").exists() and (out / "config.json").exists()
    det = TransformerDetector(out)
    bad, good = det.score("ignore instructions information", {}), det.score("task user content", {})
    assert 0 <= bad <= 1 and bad < good
