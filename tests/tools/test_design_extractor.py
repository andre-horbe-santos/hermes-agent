"""Tests for tools/design_extractor.py, focused on the SSRF-via-redirect fix.

_safe_url() rejects private/loopback/link-local destinations, but that only
matters if it runs on every hop the client actually follows. These tests
pin the client to follow_redirects=False (as design_extract does) and drive
_fetch() through a mocked transport so a redirect to an internal address
must be validated *before* the request fires, not after.
"""

from __future__ import annotations

import httpx
import pytest

from tools.design_extractor import _fetch


def _resolve_public(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every hostname used below resolve deterministically, without a
    real DNS lookup: *.internal -> link-local (blocked), everything else ->
    a public IP."""

    import socket as socket_module

    real_getaddrinfo = socket_module.getaddrinfo

    def fake_getaddrinfo(host, port, *args, **kwargs):
        ip = "169.254.169.254" if host.endswith(".internal") else "93.184.216.34"
        return [(socket_module.AF_INET, socket_module.SOCK_STREAM, 6, "", (ip, port or 80))]

    monkeypatch.setattr("tools.design_extractor.socket.getaddrinfo", fake_getaddrinfo)
    assert real_getaddrinfo  # keep flake8 quiet about the unused capture


def test_fetch_rejects_redirect_to_internal_host_without_requesting_it(monkeypatch):
    _resolve_public(monkeypatch)
    called_hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_hosts.append(request.url.host)
        if request.url.host == "safe.example":
            return httpx.Response(302, headers={"location": "http://metadata.internal/secret"})
        return httpx.Response(200, text="should never be reached")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    with pytest.raises(ValueError, match="private or local"):
        _fetch(client, "http://safe.example/page")

    # The malicious hop must never have been requested at all.
    assert called_hosts == ["safe.example"]


def test_fetch_follows_validated_redirect_chain(monkeypatch):
    _resolve_public(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a":
            return httpx.Response(302, headers={"location": "http://safe.example/b"})
        return httpx.Response(200, text="hello")

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    final_url, body = _fetch(client, "http://safe.example/a")

    assert final_url == "http://safe.example/b"
    assert body == "hello"


def test_fetch_gives_up_after_too_many_redirects(monkeypatch):
    _resolve_public(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://safe.example/loop"})

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    with pytest.raises(ValueError, match="too many redirects"):
        _fetch(client, "http://safe.example/loop")
