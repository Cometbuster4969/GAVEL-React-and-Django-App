"""
Production security middleware for Gavel.
Includes HTTPS enforcement, secure headers, rate limiting, and secret validation.
"""
import os
import time
from collections import defaultdict

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


# Rate limiting: in-memory per-IP tracking (production recommendation: Redis-backed)
_rate_limit_store = defaultdict(lambda: {"count": 0, "reset": time.time() + 60})


class RateLimitMiddleware:
    """Simple per-IP rate limiting for API endpoints. Production should use Django-Ratelimit or Redis."""
    LIMIT = 100  # requests per minute per IP
    WINDOW = 60  # seconds

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only rate-limit API routes
        path = request.path
        if not path.startswith("/api/v1/"):
            return self.get_response(request)

        # Skip health endpoint
        if path == "/api/v1/health":
            return self.get_response(request)

        client_ip = self._get_client_ip(request)
        now = time.time()
        entry = _rate_limit_store[client_ip]

        # Reset window if expired
        if now > entry["reset"]:
            entry["count"] = 0
            entry["reset"] = now + self.WINDOW

        entry["count"] += 1

        if entry["count"] > self.LIMIT:
            from apps.shared.errors import AppError
            from rest_framework.response import Response
            return Response(
                {"error": {"code": "RATE_LIMITED", "message": "Too many requests. Please slow down."}},
                status=429,
            )

        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(self.LIMIT)
        response["X-RateLimit-Remaining"] = str(max(0, self.LIMIT - entry["count"]))
        response["X-RateLimit-Reset"] = str(int(entry["reset"]))
        return response

    def _get_client_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")


class SecretValidationMiddleware:
    """Warn or block startup if development secrets are still in use."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check JWT secret at runtime for production safety
        jwt_secret = getattr(settings, "JWT_SECRET", "")
        if not settings.DEBUG and ("demo" in jwt_secret.lower() or "local" in jwt_secret.lower() or len(jwt_secret) < 32):
            # In production, return 503 until secrets are rotated
            from rest_framework.response import Response
            return Response(
                {"error": {"code": "CONFIG_ERROR", "message": "Production JWT secret is not configured securely."}},
                status=503,
            )
        return self.get_response(request)
