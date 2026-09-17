"""
MAPIS Trust Scorer
==================
The core of MAPIS. Maintains stateful session history per agent channel
and computes a rolling trust score for every inter-agent message.

Trust score: 0.0 = fully trusted, 1.0 = fully malicious
"""

import re
import json
import hashlib
from datetime import datetime
from typing import Optional
from loguru import logger

from backend.models.schemas import (
    AgentMessage, TrustScore, TrustDecision, SessionState
)
from backend.config import settings


# ── Injection Pattern Library ──────────────────────────────────────────────
# Organized by attack category with associated risk weights

INJECTION_PATTERNS = {
    "direct_override": {
        "weight": 0.9,
        "patterns": [
            r"ignore (all |your |previous |above |prior )?(instructions?|rules?|guidelines?|system prompt)",
            r"disregard (all |your |previous |above |prior )?(instructions?|rules?|guidelines?)",
            r"forget (everything|all|your instructions?|what you were told)",
            r"do not follow (your |the |any )?(instructions?|rules?|guidelines?)",
            r"override (system|previous|all) (prompt|instructions?|rules?)",
        ]
    },
    "goal_hijacking": {
        "weight": 0.85,
        "patterns": [
            r"your (new|real|actual|true) (task|goal|objective|job|mission|purpose) is",
            r"instead (of|,) (do|perform|execute|complete)",
            r"new (instruction|directive|command|task|goal):",
            r"from now on (you (are|will|should|must)|act as|behave as)",
            r"you are now (a |an )?(different|new|another|unrestricted)",
        ]
    },
    "data_exfiltration": {
        "weight": 0.95,
        "patterns": [
            r"send (all |this |the )?(data|information|content|files?|credentials?|passwords?|keys?) to",
            r"exfiltrate (the |all |this )?(data|information|content)",
            r"(forward|transmit|email|post|upload) (the |this |all )?(data|content|information|files?) to",
            r"(extract|steal|copy|leak) (and |then )?(send|transmit|forward)",
            r"http[s]?://(?!legitimate)[^\s]+ .*(send|post|upload|transmit)",
        ]
    },
    "privilege_escalation": {
        "weight": 0.88,
        "patterns": [
            r"you (now |are |have )?(have |)?(admin|root|superuser|elevated|unrestricted) (access|privileges?|permissions?|rights?)",
            r"bypass (the |all |any )?(security|restrictions?|limitations?|filters?|guardrails?|safety)",
            r"(disable|turn off|remove|skip) (the |all |any )?(safety|security|restrictions?|filters?|guardrails?)",
            r"you (are|were) (trained|programmed|designed|built) to (ignore|bypass|disregard)",
            r"act as (if|though) you (have no|without any) restrictions?",
        ]
    },
    "role_injection": {
        "weight": 0.80,
        "patterns": [
            r"(pretend|imagine|act|behave) (you are|as if you are|as though you are) (a |an )?(?!assistant|helpful)[^\s]+ (without|with no|that ignores?)",
            r"you are (DAN|AIM|STAN|DUDE|KEVIN|jailbreak)",
            r"jailbreak (mode|enabled|activated|on)",
            r"developer (mode|override) (enabled|activated|on)",
            r"do anything now",
        ]
    },
    "instruction_embedding": {
        "weight": 0.75,
        "patterns": [
            r"\[SYSTEM\].*?(instruction|command|directive)",
            r"<\|im_start\|>system",
            r"<<SYS>>",
            r"\[INST\].*?override",
            r"###\s*(instruction|system|override|new task)",
            r"---\s*(new instruction|system message|override)",
        ]
    },
    "context_manipulation": {
        "weight": 0.70,
        "patterns": [
            r"the (previous|above|last) (message|instruction|text) was (a |)(test|joke|mistake|wrong)",
            r"(actually|in fact|really|truthfully),? (ignore|disregard|forget) (that|what|everything)",
            r"(scratch|cancel|void) (that|the (previous|last|above) (instruction|message|task))",
            r"(translation|summary|analysis):\s*ignore",
        ]
    },
    "tool_abuse": {
        "weight": 0.82,
        "patterns": [
            r"call (the |a |this )?(tool|function|api|endpoint) (to |and )?(delete|destroy|format|wipe|rm -rf)",
            r"execute (this |the |a )?(command|script|code|shell).*?(rm|del|format|shutdown|reboot)",
            r"(run|execute|invoke) (as |with )?(root|admin|sudo|elevated)",
        ]
    }
}

# ── Behavioral Drift Indicators ────────────────────────────────────────────
# These are subtle signals that accumulate over a session

DRIFT_INDICATORS = [
    r"(however|but|although|nevertheless|despite this),? (you (should|must|can|will|are allowed to))",
    r"(in this (context|case|scenario|situation)),? (the rules?|restrictions?|guidelines?) (do not apply|don't apply|are different)",
    r"(hypothetically|theoretically|in a fictional scenario|imagine if)",
    r"(as (an|a) (example|exercise|demonstration|test)),? (what would|how would|could you)",
    r"(confidentially|between us|just this once|off the record)",
]


class TrustScorer:
    """
    Stateful trust scorer that maintains session history per agent channel
    and computes rolling trust scores based on accumulated evidence.
    """

    def __init__(self):
        # In-memory session store: session_id -> SessionState
        # In production this is backed by Redis (see session_manager.py)
        self._sessions: dict[str, SessionState] = {}

    # ── Public API ─────────────────────────────────────────────────────────

    def score_message(
        self,
        session_id: str,
        source_agent: str,
        target_agent: str,
        message: str,
        metadata: Optional[dict] = None
    ) -> TrustScore:
        """
        Main entry point. Score a message in the context of its session history.
        Returns a TrustScore with decision, score, and explanation.
        """
        # Get or create session
        session = self._get_or_create_session(session_id)

        # 1. Pattern-based injection detection
        pattern_score, pattern_hits = self._detect_patterns(message)

        # 2. Behavioral drift detection (subtle manipulation over time)
        drift_score, drift_hits = self._detect_drift(message, session)

        # 3. Session anomaly score (based on history)
        anomaly_score = self._compute_session_anomaly(session, source_agent, message)

        # 4. Entropy / obfuscation detection
        entropy_score = self._detect_obfuscation(message)

        # 5. Combine scores with weights
        raw_score = (
            pattern_score   * 0.45 +
            drift_score     * 0.20 +
            anomaly_score   * 0.25 +
            entropy_score   * 0.10
        )

        # 6. Apply session penalty: if previous messages were suspicious,
        #    raise the score of current message (stateful memory effect)
        session_penalty = self._compute_session_penalty(session)
        final_score = min(1.0, raw_score + session_penalty)

        # 7. Determine decision
        decision = self._decide(final_score)

        # 8. Build trust score object
        trust_score = TrustScore(
            session_id=session_id,
            source_agent=source_agent,
            target_agent=target_agent,
            message_hash=self._hash_message(message),
            raw_score=round(raw_score, 4),
            session_penalty=round(session_penalty, 4),
            final_score=round(final_score, 4),
            decision=decision,
            pattern_hits=pattern_hits,
            drift_hits=drift_hits,
            explanation=self._build_explanation(
                final_score, decision, pattern_hits, drift_hits,
                anomaly_score, entropy_score
            ),
            timestamp=datetime.utcnow().isoformat()
        )

        # 9. Update session history (stateful update)
        self._update_session(session, session_id, source_agent, message, trust_score)

        logger.info(
            f"[MAPIS] {source_agent} → {target_agent} | "
            f"Score: {final_score:.3f} | Decision: {decision} | "
            f"Hits: {len(pattern_hits)}"
        )

        return trust_score

    def get_session_summary(self, session_id: str) -> dict:
        """Get full session history and statistics."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}
        return {
            "session_id": session_id,
            "message_count": len(session.messages),
            "average_score": session.average_score,
            "max_score": session.max_score,
            "blocked_count": session.blocked_count,
            "warned_count": session.warned_count,
            "messages": [m.dict() for m in session.messages[-20:]]  # last 20
        }

    def clear_session(self, session_id: str):
        """Clear session state (e.g., after task completion)."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"[MAPIS] Session {session_id} cleared")

    # ── Pattern Detection ──────────────────────────────────────────────────

    def _detect_patterns(self, message: str) -> tuple[float, list[dict]]:
        """
        Scan message against all injection pattern categories.
        Returns max weighted score and list of hits.
        """
        message_lower = message.lower()
        hits = []
        max_weight = 0.0

        for category, config in INJECTION_PATTERNS.items():
            weight = config["weight"]
            for pattern in config["patterns"]:
                match = re.search(pattern, message_lower, re.IGNORECASE | re.DOTALL)
                if match:
                    hits.append({
                        "category": category,
                        "weight": weight,
                        "matched_text": match.group(0)[:100],
                        "pattern": pattern
                    })
                    max_weight = max(max_weight, weight)
                    break  # one hit per category is enough

        # If multiple categories hit, compound the score
        if len(hits) > 1:
            compound_bonus = min(0.15, len(hits) * 0.03)
            max_weight = min(1.0, max_weight + compound_bonus)

        return max_weight, hits

    def _detect_drift(
        self, message: str, session: "SessionState"
    ) -> tuple[float, list[str]]:
        """
        Detect subtle behavioral drift signals that accumulate across messages.
        Single message might score low, but pattern across session is caught.
        """
        message_lower = message.lower()
        hits = []

        for pattern in DRIFT_INDICATORS:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                hits.append(match.group(0)[:80])

        # Check for goal drift vs session baseline
        goal_drift_score = 0.0
        if session.baseline_intent and len(session.messages) > 3:
            goal_drift_score = self._measure_goal_drift(
                message, session.baseline_intent
            )

        base_score = min(1.0, len(hits) * 0.15)
        combined = min(1.0, base_score + goal_drift_score)

        return combined, hits

    def _measure_goal_drift(self, message: str, baseline: str) -> float:
        """
        Simple lexical drift measurement: how different is this message
        from the session's established intent/baseline?
        """
        baseline_words = set(baseline.lower().split())
        message_words = set(message.lower().split())

        if not baseline_words:
            return 0.0

        overlap = baseline_words & message_words
        overlap_ratio = len(overlap) / len(baseline_words)

        # Low overlap with baseline = potential drift
        drift = 1.0 - overlap_ratio

        # Only flag if drift is very high (>80% different from baseline)
        return max(0.0, drift - 0.8) * 2.0  # scale to 0-0.4 range

    # ── Session Anomaly Detection ──────────────────────────────────────────

    def _compute_session_anomaly(
        self, session: "SessionState", source_agent: str, message: str
    ) -> float:
        """
        Detect anomalies based on session history:
        - Sudden topic/goal shift after multiple normal messages
        - Unusual agent communication patterns
        - Message length anomalies
        """
        score = 0.0

        if len(session.messages) < 2:
            return 0.0

        # 1. Message length anomaly (injection payloads tend to be long)
        avg_len = sum(len(m.content) for m in session.messages) / len(session.messages)
        current_len = len(message)
        if avg_len > 0 and current_len > avg_len * 3:
            score += 0.15  # this message is 3x longer than average

        # 2. Unusual source agent (agent that hasn't communicated before)
        known_agents = set(m.source_agent for m in session.messages)
        if source_agent not in known_agents and len(known_agents) > 2:
            score += 0.10

        # 3. Rapid score escalation in recent history
        recent_scores = [
            m.trust_score for m in session.messages[-5:]
            if m.trust_score is not None
        ]
        if recent_scores and len(recent_scores) >= 2:
            escalation = recent_scores[-1] - recent_scores[0]
            if escalation > 0.3:  # scores rising fast
                score += 0.20

        return min(1.0, score)

    def _compute_session_penalty(self, session: "SessionState") -> float:
        """
        If previous messages in this session were suspicious,
        apply a penalty to the current message's score.
        This is the key stateful contribution of MAPIS.
        """
        if not session.messages:
            return 0.0

        recent = session.messages[-5:]  # look at last 5 messages
        suspicious_count = sum(
            1 for m in recent
            if m.trust_score is not None and m.trust_score > 0.4
        )

        # More suspicious history = higher penalty on current message
        if suspicious_count >= 4:
            return 0.25
        elif suspicious_count >= 3:
            return 0.15
        elif suspicious_count >= 2:
            return 0.08
        elif suspicious_count >= 1:
            return 0.03
        return 0.0

    # ── Obfuscation Detection ──────────────────────────────────────────────

    def _detect_obfuscation(self, message: str) -> float:
        """
        Detect encoding/obfuscation tricks used to evade pattern matching.
        """
        score = 0.0

        # Base64-like chunks in unexpected places
        b64_pattern = r'[A-Za-z0-9+/]{40,}={0,2}'
        if re.search(b64_pattern, message):
            score += 0.15

        # Unicode lookalike characters (homoglyph attacks)
        suspicious_unicode = sum(1 for c in message if ord(c) > 0x2000 and ord(c) < 0xFFFF)
        if suspicious_unicode > 5:
            score += 0.20

        # Zero-width characters (invisible injection)
        zero_width = sum(1 for c in message if c in '\u200b\u200c\u200d\ufeff')
        if zero_width > 0:
            score += 0.35

        # Excessive special characters ratio
        special_chars = sum(1 for c in message if not c.isalnum() and c not in ' .,!?-_\n\t')
        if len(message) > 0 and special_chars / len(message) > 0.4:
            score += 0.15

        return min(1.0, score)

    # ── Decision Making ────────────────────────────────────────────────────

    def _decide(self, score: float) -> TrustDecision:
        """Map score to decision based on configured thresholds."""
        if score < settings.TRUST_BLOCK_THRESHOLD:
            return TrustDecision.ALLOW
        elif score < settings.TRUST_WARN_THRESHOLD:
            return TrustDecision.WARN
        else:
            return TrustDecision.BLOCK

    def _build_explanation(
        self,
        score: float,
        decision: TrustDecision,
        pattern_hits: list,
        drift_hits: list,
        anomaly_score: float,
        entropy_score: float
    ) -> str:
        """Human-readable explanation of the trust decision."""
        parts = []

        if pattern_hits:
            categories = list(set(h["category"] for h in pattern_hits))
            parts.append(
                f"Detected injection patterns: {', '.join(categories)} "
                f"({len(pattern_hits)} match{'es' if len(pattern_hits) > 1 else ''})"
            )

        if drift_hits:
            parts.append(
                f"Behavioral drift signals detected ({len(drift_hits)} indicator{'s' if len(drift_hits) > 1 else ''})"
            )

        if anomaly_score > 0.1:
            parts.append(f"Session anomaly detected (score: {anomaly_score:.2f})")

        if entropy_score > 0.1:
            parts.append(f"Possible obfuscation/encoding detected (score: {entropy_score:.2f})")

        if not parts:
            parts.append("No injection signals detected")

        decision_text = {
            TrustDecision.ALLOW: "Message allowed",
            TrustDecision.WARN: "Message flagged for review",
            TrustDecision.BLOCK: "Message BLOCKED - suspected injection attack"
        }[decision]

        return f"{decision_text} (score: {score:.3f}). " + ". ".join(parts) + "."

    # ── Session Management ─────────────────────────────────────────────────

    def _get_or_create_session(self, session_id: str) -> "SessionState":
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id]

    def _update_session(
        self,
        session: "SessionState",
        session_id: str,
        source_agent: str,
        message: str,
        trust_score: "TrustScore"
    ):
        """Add message to session history and update session statistics."""
        from backend.models.schemas import MessageRecord

        record = MessageRecord(
            source_agent=source_agent,
            content=message[:500],  # store truncated for memory efficiency
            trust_score=trust_score.final_score,
            decision=trust_score.decision,
            timestamp=trust_score.timestamp
        )

        session.messages.append(record)

        # Enforce history limit
        if len(session.messages) > settings.SESSION_HISTORY_LIMIT:
            session.messages = session.messages[-settings.SESSION_HISTORY_LIMIT:]

        # Update statistics
        all_scores = [m.trust_score for m in session.messages if m.trust_score is not None]
        session.average_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
        session.max_score = max(all_scores) if all_scores else 0.0
        session.blocked_count = sum(1 for m in session.messages if m.decision == TrustDecision.BLOCK)
        session.warned_count = sum(1 for m in session.messages if m.decision == TrustDecision.WARN)

        # Set baseline intent from first message (if not set)
        if not session.baseline_intent and len(session.messages) == 1:
            session.baseline_intent = message[:200]

    @staticmethod
    def _hash_message(message: str) -> str:
        return hashlib.sha256(message.encode()).hexdigest()[:16]


# Singleton instance
trust_scorer = TrustScorer()
