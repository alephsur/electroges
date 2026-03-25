from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hashing():
    password = "test_password_123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)


def test_access_token():
    data = {"sub": "test@example.com"}
    token = create_access_token(data)
    decoded = decode_token(token)
    assert decoded["sub"] == "test@example.com"
    assert decoded["type"] == "access"
