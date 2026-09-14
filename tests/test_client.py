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
