import pytest
from fastapi import status

def test_register_user(client):
    """Test user registration."""
    payload = {
        "email": "test@user.com",
        "full_name": "Test User",
        "password": "securepassword123"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    
    data = response.json()
    assert data["email"] == "test@user.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert "password" not in data

def test_register_duplicate_user(client):
    """Test user registration with existing email fails."""
    payload = {
        "email": "test@user.com",
        "full_name": "Test User",
        "password": "securepassword123"
    }
    client.post("/api/auth/register", json=payload)
    
    # Try duplicate signup
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in response.json()["detail"]

def test_login_user(client):
    """Test login gets token and sets auth cookie."""
    # Register first
    client.post("/api/auth/register", json={
        "email": "test@user.com",
        "full_name": "Test User",
        "password": "securepassword123"
    })
    
    # Login via form-urlencoded
    form_data = {
        "username": "test@user.com",
        "password": "securepassword123"
    }
    response = client.post("/api/auth/login", data=form_data)
    assert response.status_code == status.HTTP_200_OK
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Check that HTTPOnly cookie was set
    assert "access_token" in response.cookies
    cookie_val = response.cookies["access_token"].strip('"')
    assert cookie_val.startswith("Bearer ")

def test_me_profile(client):
    """Test reading logged-in profile data."""
    # Register
    client.post("/api/auth/register", json={
        "email": "test@user.com",
        "full_name": "Test User",
        "password": "securepassword123"
    })
    
    # Login to set cookie
    login_res = client.post("/api/auth/login", data={
        "username": "test@user.com",
        "password": "securepassword123"
    })
    
    # Check /me profile endpoint
    response = client.get("/api/auth/me")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "test@user.com"
    assert data["full_name"] == "Test User"
