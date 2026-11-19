import pytest

from unleak.detectors import scan
from unleak.detectors.pii import cnpj_is_valid, cpf_is_valid, luhn_is_valid


def kinds(text, **kw):
    return [(m.kind, m.text) for m in scan(text, **kw)]


# All values below are fake and exist only for these tests.
@pytest.mark.parametrize(
    "text,kind,expected",
    [
        ("Contact:jane.doe@example.com now", "email", "jane.doe@example.com"),
        ("CPF529.982.247-25", "cpf", "529.982.247-25"),
        ("cpf 52998224725", "cpf", "52998224725"),
        ("CNPJ 11.222.333/0001-81", "cnpj", "11.222.333/0001-81"),
        ("card 4242 4242 4242 4242 exp", "card", "4242 4242 4242 4242"),
        ("call +55 11 91234-5678", "phone", "+55 11 91234-5678"),
        ("fone(11)91234-5678", "phone", "(11)91234-5678"),
        ("us +1 415 555 2671", "phone", "+1 415 555 2671"),
        ("server 203.0.113.42 up", "ip", "203.0.113.42"),
        ("KEY=sk-ant-api03-FAKEfake1234567890abcdefXYZ", "secret", "sk-ant-api03-FAKEfake1234567890abcdefXYZ"),
        ("ghp_FAKE567890abcdefghijklmnopqrstuvwxyz12", "secret", "ghp_FAKE567890abcdefghijklmnopqrstuvwxyz12"),
        ("aws AKIAFAKEFAKEFAKE1234", "secret", "AKIAFAKEFAKEFAKE1234"),
        ("password: hunter2", "credential", "hunter2"),
        ('"senha":"abc123"', "credential", "abc123"),
        ("DB_TOKEN=a1b2c3d4e5f6g7", "credential", "a1b2c3d4e5f6g7"),
        ("x Zx9Kq2Lm8Pv4Rt6Yw1Bn3Cd5Fg7Hj0AsQeUi y", "token", "Zx9Kq2Lm8Pv4Rt6Yw1Bn3Cd5Fg7Hj0AsQeUi"),
    ],
)
def test_detects(text, kind, expected):
    assert (kind, expected) in kinds(text)


@pytest.mark.parametrize(
    "text",
    [
        "version 1.2.3 released on 2026-11-19 at 10:30",
        "CPF 111.111.111-11",          # repeated digits
        "CPF 529.982.247-26",          # wrong check digit
        "card 4242 4242 4242 4243",    # fails Luhn
        "commit 3f2a9c1d8e7b6a5f4e3d2c1b0a9f8e7d6c5b4a39",  # git hash
        "listening on 127.0.0.1 and 0.0.0.0",
        "token: true",
        "password=",
        "The quick brown fox jumps over the lazy dog",
        "width=1920 height=1080 fps=30",
        "open https://example.com:8080/docs and http://localhost:3000",
    ],
)
def test_ignores(text):
    assert kinds(text) == []


def test_ocr_without_spaces():
    found = kinds("Contact:jane.doe@example.com+551191234-5678")
    assert ("email", "jane.doe@example.com") in found
    assert ("phone", "+551191234-5678") in found


def test_custom_literals_ignore_case_and_spaces():
    assert kinds("Invoice for AcmeCorp Ltd", also=["acme corp"]) == [("custom", "AcmeCorp")]


def test_kind_filter():
    text = "jane@example.com 203.0.113.42"
    assert kinds(text, kinds=["email"]) == [("email", "jane@example.com")]


def test_overlaps_merge_into_one_span():
    found = scan("API_KEY=sk-ant-api03-FAKEfake1234567890abcdefXYZ")
    assert len(found) == 1 and found[0].kind == "secret"


def test_validators():
    assert cpf_is_valid("529.982.247-25") and not cpf_is_valid("123.456.789-00")
    assert cnpj_is_valid("11.222.333/0001-81") and not cnpj_is_valid("11.222.333/0001-82")
    assert luhn_is_valid("4242424242424242") and not luhn_is_valid("4242424242424241")


def test_connection_string_password():
    found = scan("DATABASE_URL=postgres://shop:Tr0ub4dor&3@db.internal:5432/shop")
    assert len(found) == 1 and found[0].kind == "credential"
    assert found[0].text.startswith("Tr0ub4dor&3")
