"""Hugging Face model factory.  It performs no download or training at import."""

from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .config import TrainingConfig


ID2LABEL = {0: "MALICIOUS", 1: "SAFE"}
LABEL2ID = {label: idx for idx, label in ID2LABEL.items()}


def load_model_and_tokenizer(config: TrainingConfig):
    """Create a binary sequence classifier when an explicit training run starts."""
    tokenizer = AutoTokenizer.from_pretrained(config.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        config.model_name,
        num_labels=2,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    return model, tokenizer
