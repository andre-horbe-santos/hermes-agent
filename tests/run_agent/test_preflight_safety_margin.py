"""Tests for the preflight compression safety margin gate."""

from unittest.mock import patch

from agent.turn_context import _should_run_preflight_estimate


def test_preflight_gate_triggers_before_the_exact_threshold():
    messages = [{"role": "user", "content": "hello"}]

    with patch(
        "agent.turn_context.estimate_messages_tokens_rough",
        return_value=91_000,
    ):
        assert _should_run_preflight_estimate(messages, 3, 20, 100_000) is True


def test_preflight_gate_stays_closed_outside_the_margin():
    messages = [{"role": "user", "content": "hello"}]

    with patch(
        "agent.turn_context.estimate_messages_tokens_rough",
        return_value=88_000,
    ):
        assert _should_run_preflight_estimate(messages, 3, 20, 100_000) is False
