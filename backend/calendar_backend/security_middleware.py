"""
Production security middleware for Gavel.
Includes HTTPS enforcement, secure headers, rate limiting, and secret validation.
"""
import ipaddress
import time

from django.http import HttpResponse
from django.conf import settings


class HTTPSRedirectMiddleware:
    """Redirect all HTTP requests to HTTPS in production."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # In production (DEBUG=False), enforce HTTPS
        if (not settings.DEBUG and
            not request.is_secure() and
            request.path != "/api/v1/health"):
            url = request.build_absolute_uri()
            secure_url = url.replace("http://", "https://", 1)
            return HttpResponse(
                f'<a href="{secure_url}">Redirect to secure URL</a>',
                status=301,
                headers={"Location": secure_url},
            )
        response = self.get_response(request)
        # Add security headers
        response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "DENY"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self';"
        return response


class RateLimitMiddleware:
    """Atomic MongoDB fixed-window counters shared by all API processes."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = getattr(settings, "RATE_LIMIT_MAX", 100)
        self.window = getattr(settings, "RATE_LIMIT_WINDOW", 60)
        self.proxies = [ipaddress.ip_network(cidr.strip()) for cidr in getattr(settings, "TRUSTED_PROXY_CIDRS", [])]
        self._collection = None

    def _counters(self):
        if self._collection is None:
            from mongoengine.connection import get_db
            collection = get_db()["ratelimitcounters"]
            collection.create_index("expiresAt", expireAfterSeconds=0, name="rate_limit_expiry")
            self._collection = collection
        return self._collection

    def __call__(self, request):
        if not request.path.startswith("/api/v1/") or request.path == "/api/v1/health":
            return self.get_response(request)
        from datetime import datetime, timezone
        from hashlib import sha256
        from django.http import JsonResponse
        from pymongo import ReturnDocument
        from pymongo.errors import DuplicateKeyError

        client_ip = self._get_client_ip(request)
        now = time.time()
        bucket = int(now // self.window)
        reset = (bucket + 1) * self.window
        counter_id = f"{sha256(client_ip.encode()).hexdigest()}:{self.window}:{bucket}"
        try:
            counters = self._counters()
            update = {"$inc": {"count": 1}, "$setOnInsert": {
                "expiresAt": datetime.fromtimestamp(reset + self.window, timezone.utc)}}
            try:
                entry = counters.find_one_and_update({"_id": counter_id}, update, upsert=True,
                                                     return_document=ReturnDocument.AFTER)
            except DuplicateKeyError:
                entry = counters.find_one_and_update({"_id": counter_id}, {"$inc": {"count": 1}},
                                                     return_document=ReturnDocument.AFTER)
            count = entry["count"]
        except Exception:
            # Never bypass the limiter during a database outage.
            return JsonResponse({"error": {"code": "RATE_LIMIT_UNAVAILABLE", "message": "Request protection is unavailable. Try again shortly."}}, status=503)
        if count > self.limit:
            response = JsonResponse({"error": {"code": "RATE_LIMITED", "message": "Too many requests. Please slow down."}}, status=429)
            response["Retry-After"] = str(max(1, int(reset - now)))
        else:
            response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(self.limit)
        response["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
        response["X-RateLimit-Reset"] = str(reset)
        return response

    def _get_client_ip(self, request):
        def parse(value):
            try:
                return ipaddress.ip_address(value.strip())
            except ValueError:
                return None

        peer = parse(request.META.get("REMOTE_ADDR", ""))
        trusted = lambda address: address is not None and any(address in network for network in self.proxies)
        if not trusted(peer):
            return str(peer) if peer else "unknown"
        # Walk from the trusted peer toward the client, not from an attacker-
        # controlled leftmost header. Malformed chains fall back to the peer.
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        chain = [parse(value) for value in forwarded.split(",")]
        if any(value is None for value in chain) or len(chain) > 32:
            return str(peer)
        for address in reversed(chain):
            if not trusted(address):
                return str(address)
        return str(peer)


class SecretValidationMiddleware:
    """Warn or block startup if development secrets are still in use."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check JWT secret at runtime for production safety
        jwt_secret = getattr(settings, "JWT_SECRET", "")
        if not settings.DEBUG and ("demo" in jwt_secret.lower() or "local" in jwt_secret.lower() or len(jwt_secret) < 32):
            # In production, return 503 until secrets are rotated
            from django.http import JsonResponse
            return JsonResponse(
                {"error": {"code": "CONFIG_ERROR", "message": "Production JWT secret is not configured securely."}},
                status=503,
            )
        return self.get_response(request)
