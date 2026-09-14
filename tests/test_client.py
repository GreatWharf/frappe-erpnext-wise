import pytest

from wise_bank_feed.client import WiseClient, WiseError


class Response:
    def __init__(self, data, status=200, headers=None):
        import json

        self.content = json.dumps(data).encode()
        self.status_code = status
        self.headers = headers or {}


class Session:
    def __init__(self, rows):
        self.rows, self.calls = iter(rows), []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.rows)

    def close(self):
        pass


def test_cursor_pagination_and_readonly():
    session = Session(
        [
            Response({"activities": [{"id": "a"}], "cursor": "next"}),
            Response({"activities": [{"id": "b"}], "cursor": None}),
        ]
    )
    client = WiseClient("secret", session=session)
    assert [x["id"] for x in client.activities("12", "start", "end")] == ["a", "b"]
    assert session.calls[1][1]["params"]["nextCursor"] == "next"
    assert all(x[1]["allow_redirects"] is False for x in session.calls)
    with pytest.raises(ValueError):
        client.get("/payments")
    with pytest.raises(ValueError):
        client.balances("../../bad")


def test_repeated_cursor_fails():
    session = Session(
        [Response({"activities": [], "cursor": "x"}), Response({"activities": [], "cursor": "x"})]
    )
    with pytest.raises(WiseError):
        list(WiseClient("secret", session=session).activities("12", "a", "b"))


def test_sca_error_does_not_leak():
    session = Session([Response({"message": "private"}, 403, {"x-2fa-approval": "sensitive"})])
    with pytest.raises(WiseError) as exc:
        WiseClient("secret", session=session).profiles()
    assert exc.value.sca and exc.value.status == 403
    assert "private" not in str(exc.value) and "sensitive" not in str(exc.value)


@pytest.mark.parametrize("cursor", [False, 0, [], {}])
def test_malformed_cursor_never_marks_history_complete(cursor):
    session = Session([Response({"activities": [], "cursor": cursor})])
    with pytest.raises(WiseError, match="pagination"):
        list(WiseClient("secret", session=session).activities("12", "a", "b"))


def test_missing_cursor_never_marks_history_complete():
    session = Session([Response({"activities": []})])
    with pytest.raises(WiseError, match="schema"):
        list(WiseClient("secret", session=session).activities("12", "a", "b"))


def test_transient_network_failure_is_retried_without_exposing_request(monkeypatch):
    import requests

    from wise_bank_feed import client as module

    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)

    class FlakySession(Session):
        def get(self, url, **kwargs):
            if not self.calls:
                self.calls.append((url, kwargs))
                raise requests.ConnectionError("Authorization: Bearer secret")
            return super().get(url, **kwargs)

    session = FlakySession([Response([{"id": 123, "type": "business"}])])
    assert WiseClient("secret", session=session).profiles() == [{"id": 123, "type": "business"}]
    assert len(session.calls) == 2


@pytest.mark.parametrize("status", [401, 403, 302])
def test_authentication_and_redirect_failures_are_not_retried(status):
    session = Session([Response({"error": "private"}, status, {"Location": "https://evil.invalid"})])
    with pytest.raises(WiseError) as exc:
        WiseClient("secret", session=session).profiles()
    assert exc.value.status == status
    assert len(session.calls) == 1 and "private" not in str(exc.value)


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_retryable_http_error_recovers(monkeypatch, status):
    from wise_bank_feed import client as module

    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    session = Session(
        [Response({}, status, {"Retry-After": "1"}), Response([{"id": 12, "type": "business"}])]
    )
    assert WiseClient("secret", session=session).profiles()[0]["id"] == 12
    assert len(session.calls) == 2


def test_network_retries_are_bounded_and_redacted(monkeypatch):
    import requests

    from wise_bank_feed import client as module

    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)

    class OfflineSession(Session):
        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            raise requests.Timeout("Bearer secret and private response")

    session = OfflineSession([])
    with pytest.raises(WiseError) as exc:
        WiseClient("secret", session=session).profiles()
    assert len(session.calls) == 3
    assert "secret" not in str(exc.value) and "private" not in str(exc.value)


def test_long_retry_after_defers_to_later_job(monkeypatch):
    from wise_bank_feed import client as module

    def must_not_sleep(seconds):
        pytest.fail("A long rate limit must not monopolize a worker")

    monkeypatch.setattr(module.time, "sleep", must_not_sleep)
    with pytest.raises(WiseError) as exc:
        WiseClient("secret", session=Session([Response({}, 429, {"Retry-After": "3600"})])).profiles()
    assert exc.value.status == 429


def test_page_limit_fails_instead_of_silently_truncating_history():
    pages = [Response({"activities": [], "cursor": str(n)}) for n in range(100)]
    with pytest.raises(WiseError, match="page limit"):
        list(WiseClient("secret", session=Session(pages)).activities("12", "start", "end"))


def test_statement_uses_compact_and_retains_decimal_digits():
    response = Response({})
    response.content = b'{"transactions":[{"amount":{"value":0.1234567890123456789,"currency":"GBP"}}]}'
    session = Session([response])
    rows = WiseClient("secret", environment="Sandbox", session=session).statement(
        "12", "64", "GBP", "start", "end"
    )
    assert rows[0]["amount"]["value"] == "0.1234567890123456789"
    url, options = session.calls[0]
    assert url == "https://api.wise-sandbox.com/2026Q3/profiles/12/balance-statements/64/statement.json"
    assert options["params"] == {
        "currency": "GBP",
        "intervalStart": "start",
        "intervalEnd": "end",
        "type": "COMPACT",
    }


@pytest.mark.parametrize("body", [b"<html>proxy error</html>", b"{broken"])
def test_invalid_json_is_sanitized(body):
    response = Response({})
    response.content = body
    with pytest.raises(WiseError, match="invalid JSON"):
        WiseClient("secret", session=Session([response])).profiles()


def test_expired_job_time_budget_makes_no_request(monkeypatch):
    from wise_bank_feed import client as module

    session = Session([])
    client = WiseClient("secret", session=session)
    monkeypatch.setattr(module.time, "monotonic", lambda: client.deadline + 1)
    with pytest.raises(WiseError, match="time budget"):
        client.profiles()
    assert session.calls == []
