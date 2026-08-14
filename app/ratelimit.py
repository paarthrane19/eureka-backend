"""Shared rate limiter.

Now that Eureka is public, unauthenticated traffic reaches the read endpoints
directly. A generous per-IP default limit protects those routes from scraping
and abuse without getting in the way of normal browsing, while auth routes get
a much stricter explicit limit (see routers/auth.py) to blunt credential
stuffing / signup spam.

The limiter is defined here (not in main.py) so routers can import it to apply
per-route limits without creating an import cycle.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=["240/minute"])
