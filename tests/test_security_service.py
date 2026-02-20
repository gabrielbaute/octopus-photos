from app.services.security_service import SecurityService

def test_password_hashing():
    service = SecurityService()
    password = "secret_password_123"
    hashed = service.get_password_hash(password)
    
    assert hashed != password
    assert service.verify_password(password, hashed) is True
    assert service.verify_password("wrong_pass", hashed) is False

def test_token_generation_and_decode():
    service = SecurityService()
    user_id = "550e8400-e29b-41d4-a716-446655440000"
    
    token_obj = service.create_access_token({"sub": user_id})
    decoded = service.decode_token(token_obj.access_token, expected_scope="access")
    
    assert decoded.user_id == user_id