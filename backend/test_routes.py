"""
Tests for every route in app.py.

Strategy: use Flask's built-in test client to send HTTP requests, and mock
out the database/auth functions so tests don't need a real Postgres or Redis.

  patch('app.register_user', ...)  - replaces the register_user function
                                     inside app.py's namespace for the duration
                                     of the `with` block, then restores it.

  client.session_transaction()     - lets us write directly into the Flask
                                     session cookie so we can simulate a
                                     logged-in user without going through /login.
"""

from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_connection(fetchone_return=None, fetchall_return=None):
    """
    Build a fake psycopg2 connection + cursor that satisfies the
    `with get_connection() as conn: with conn.cursor() as cur:` pattern.

    fetchone_return  - what cur.fetchone() gives back
    fetchall_return  - what cur.fetchall() gives back
    """
    mock_cur = MagicMock()
    mock_cur.fetchone.return_value = fetchone_return
    mock_cur.fetchall.return_value = fetchall_return or []

    mock_conn = MagicMock()
    # __enter__ / __exit__ make `with get_connection() as conn:` work.
    mock_conn.__enter__.return_value = mock_conn
    # cursor() is also used as a context manager: `with conn.cursor() as cur:`
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur

    return mock_conn, mock_cur


# ===========================================================================
# /register
# ===========================================================================

def test_register_success(client):
    """Happy path: valid data creates a user and returns 200."""
    # patch('app.register_user') replaces the real function (which would hit
    # the database) with a fake one that just returns a user ID.
    with patch("app.register_user", return_value=42):
        response = client.post("/register", data={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass",
        })
    assert response.status_code == 200
    assert b"Registration successful" in response.data


def test_register_missing_username(client):
    """Omitting username should return 400 with a clear error message."""
    response = client.post("/register", data={
        "email": "test@example.com",
        "password": "securepass",
    })
    assert response.status_code == 400
    assert b"Username is required" in response.data


def test_register_missing_email(client):
    response = client.post("/register", data={
        "username": "testuser",
        "password": "securepass",
    })
    assert response.status_code == 400
    assert b"Email is required" in response.data


def test_register_missing_password(client):
    response = client.post("/register", data={
        "username": "testuser",
        "email": "test@example.com",
    })
    assert response.status_code == 400
    assert b"Password is required" in response.data


def test_register_invalid_email(client):
    """A string that isn't a valid email address should be rejected."""
    response = client.post("/register", data={
        "username": "testuser",
        "email": "not-an-email",
        "password": "securepass",
    })
    assert response.status_code == 400
    assert b"Invalid email format" in response.data


def test_register_password_too_short(client):
    """Passwords under 6 characters should be rejected."""
    response = client.post("/register", data={
        "username": "testuser",
        "email": "test@example.com",
        "password": "abc",
    })
    assert response.status_code == 400
    assert b"at least 6 characters" in response.data


def test_register_username_too_short(client):
    """Usernames under 3 characters should be rejected."""
    response = client.post("/register", data={
        "username": "ab",
        "email": "test@example.com",
        "password": "securepass",
    })
    assert response.status_code == 400
    assert b"between 3 and 50 characters" in response.data


def test_register_duplicate_user(client):
    """If the username/email already exists, register_user raises ValueError.
    The route should catch it and return 400."""
    with patch("app.register_user", side_effect=ValueError("Username or email already taken")):
        response = client.post("/register", data={
            "username": "testuser",
            "email": "test@example.com",
            "password": "securepass",
        })
    assert response.status_code == 400
    assert b"already taken" in response.data


# ===========================================================================
# /login
# ===========================================================================

def test_login_success(client):
    """Correct credentials return 200 and set the session."""
    with patch("app.login_user", return_value=1):
        response = client.post("/login", data={
            "username": "testuser",
            "password": "securepass",
        })
    assert response.status_code == 200
    assert b"Login successful" in response.data


def test_login_wrong_credentials(client):
    """Wrong password returns 401.
    login_user raises ValueError for bad credentials; route maps it to 401."""
    with patch("app.login_user", side_effect=ValueError("User credential incorrect.")):
        response = client.post("/login", data={
            "username": "testuser",
            "password": "wrongpassword",
        })
    assert response.status_code == 401
    assert b"credential incorrect" in response.data


def test_login_missing_username(client):
    response = client.post("/login", data={"password": "securepass"})
    assert response.status_code == 400
    assert b"Username is required" in response.data


def test_login_missing_password(client):
    response = client.post("/login", data={"username": "testuser"})
    assert response.status_code == 400
    assert b"Password is required" in response.data


# ===========================================================================
# /dashboard
# ===========================================================================

def test_dashboard_not_logged_in(client):
    """Without a session, /dashboard must return 401."""
    response = client.get("/dashboard")
    assert response.status_code == 401
    assert b"Not logged in" in response.data


def test_dashboard_logged_in(client):
    """With a valid session the route queries the DB and returns products."""
    # Write user_id=1 directly into the session cookie.
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    mock_conn, mock_cur = _mock_connection(fetchall_return=[
        (1, "YONEX Astrox 99", 199.99, 150.00, 220.00, "https://www.yonex.com/astrox-99"),
    ])

    with patch("app.get_connection", return_value=mock_conn):
        response = client.get("/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert "products" in data
    assert len(data["products"]) == 1


# ===========================================================================
# /add_product
# ===========================================================================

def test_add_product_not_logged_in(client):
    """Without a session the route must refuse before touching the scraper."""
    response = client.post("/add_product", data={
        "product_url": "https://www.yonex.com/racket",
        "target_price": "50",
    })
    assert response.status_code == 401


def test_add_product_missing_url(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/add_product", data={"target_price": "50"})
    assert response.status_code == 400
    assert b"Product URL is required" in response.data


def test_add_product_missing_target_price(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/add_product", data={
        "product_url": "https://www.yonex.com/racket",
    })
    assert response.status_code == 400
    assert b"Target price is required" in response.data


def test_add_product_invalid_url_domain(client):
    """URLs from non-allowed domains (e.g. amazon.com) must be rejected.
    This is the SSRF protection in is_valid_url()."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/add_product", data={
        "product_url": "https://www.amazon.com/dp/B123",
        "target_price": "50",
    })
    assert response.status_code == 400
    assert b"Invalid URL" in response.data


def test_add_product_price_not_a_number(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/add_product", data={
        "product_url": "https://www.yonex.com/racket",
        "target_price": "not-a-number",
    })
    assert response.status_code == 400
    assert b"valid number" in response.data


def test_add_product_negative_price(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/add_product", data={
        "product_url": "https://www.yonex.com/racket",
        "target_price": "-10",
    })
    assert response.status_code == 400
    assert b"greater than 0" in response.data


def test_add_product_target_above_current_price(client):
    """If the target price is >= the live scraped price, reject it.
    We mock the scraper so we don't make a real HTTP request."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    fake_product = {
        "product_name": "YONEX Astrox 99",
        "product_price": 80.00,
        "product_url": "https://www.yonex.com/astrox-99",
    }
    # patch scraper.return_dict so no real HTTP request is made.
    with patch("app.scraper.return_dict", return_value=fake_product):
        response = client.post("/add_product", data={
            "product_url": "https://www.yonex.com/astrox-99",
            "target_price": "100",  # above current price of 80
        })
    assert response.status_code == 400
    assert b"less than current price" in response.data


# ===========================================================================
# /delete_product
# ===========================================================================

def test_delete_product_not_logged_in(client):
    response = client.post("/delete_product", data={"product_id": "1"})
    assert response.status_code == 401


def test_delete_product_missing_id(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/delete_product", data={})
    assert response.status_code == 400
    assert b"Product ID is required" in response.data


def test_delete_product_invalid_id(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
    response = client.post("/delete_product", data={"product_id": "abc"})
    assert response.status_code == 400
    assert b"Invalid product ID" in response.data


def test_delete_product_not_owned(client):
    """If the product belongs to a different user, return 403.
    The ownership query returns None (no row found)."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    # fetchone returns None → the ownership check finds nothing → 403
    mock_conn, _ = _mock_connection(fetchone_return=None)

    with patch("app.get_connection", return_value=mock_conn):
        response = client.post("/delete_product", data={"product_id": "99"})

    assert response.status_code == 403
    assert b"unauthorized" in response.data


def test_delete_product_success(client):
    """When the user owns the product the route deletes it and returns 200."""
    with client.session_transaction() as sess:
        sess["user_id"] = 1

    # fetchone returns (1,) → ownership check passes
    mock_conn, _ = _mock_connection(fetchone_return=(1,))

    with patch("app.get_connection", return_value=mock_conn):
        response = client.post("/delete_product", data={"product_id": "1"})

    assert response.status_code == 200
    assert b"deleted successfully" in response.data
