import csv

from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response

from apps.shared.errors import AppError

from . import auth, services
from .auth import require_auth


def body_object(request):
    if not isinstance(request.data, dict):
        raise AppError(400, "INVALID_BODY", "Request body must be a JSON object.")
    return request.data


@api_view(["POST"])
def login(request):
    payload = body_object(request)
    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        raise AppError(400, "INVALID_CREDENTIALS", "Enter a valid email and password.")
    email = email.strip()
    if len(email) > 254 or "@" not in email or email.startswith("@") or email.endswith("@") or not password or len(password) > 200:
        raise AppError(400, "INVALID_CREDENTIALS", "Enter a valid email and password.")
    return Response({"data": auth.login(email, password)})


@api_view(["GET"])
@require_auth()
def me(request):
    return Response({"data": {"user": auth.public_user(request.gavel_user)}})


@api_view(["GET"])
@require_auth()
def campaigns(request):
    return Response({"data": services.list_campaigns(request.gavel_user)})


@api_view(["POST"])
@require_auth("administrator", "owner")
def create_campaign(request):
    return Response({"data": services.create_campaign(request.gavel_user, body_object(request))}, status=201)


@api_view(["POST"])
@require_auth("administrator", "owner")
def create_campaign_version(request, campaign_id):
    return Response({"data": services.create_campaign_version(request.gavel_user, campaign_id)}, status=201)


@api_view(["GET", "PATCH", "DELETE"])
@require_auth()
def campaign_detail(request, campaign_id):
    campaign = services.ensure_campaign(campaign_id)
    if request.method == "GET":
        if request.gavel_user.role == "owner":
            services.ensure_owner(request.gavel_user, campaign)
        return Response({"data": services.public_campaign(campaign)})
    if request.method == "DELETE":
        services.delete_campaign(request.gavel_user, campaign_id)
        return Response(status=204)
    return Response({"data": services.update_campaign(request.gavel_user, campaign_id, body_object(request))})


@api_view(["POST"])
@require_auth("administrator", "owner")
def campaign_transition(request, campaign_id):
    target = body_object(request).get("status")
    if not isinstance(target, str):
        raise AppError(400, "INVALID_STATUS", "Select a valid campaign status.")
    return Response({"data": services.transition_campaign(request.gavel_user, campaign_id, target)})


@api_view(["POST"])
@require_auth("administrator", "owner")
def publish_results(request, campaign_id):
    return Response({"data": services.publish_results(request.gavel_user, campaign_id)}, status=201)


@api_view(["GET"])
@require_auth("administrator", "owner", "adjudicator")
def published_results(request, campaign_id):
    return Response({"data": services.get_published_results(request.gavel_user, campaign_id)})


@api_view(["GET"])
@require_auth("administrator", "owner", "adjudicator")
def export_results(request, campaign_id):
    publication = services.get_published_results(request.gavel_user, campaign_id)
    if request.query_params.get("format", "json").lower() != "csv":
        return Response({"data": publication})
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="gavel-results-{campaign_id}.csv"'
    writer = csv.writer(response)
    writer.writerow(["model", "wins"])
    for row in publication["snapshot"].get("modelWins", []):
        writer.writerow([row.get("model", ""), row.get("wins", 0)])
    return response


@api_view(["GET", "POST"])
@require_auth()
def campaign_submissions(request, campaign_id):
    if request.method == "GET":
        return Response({"data": services.list_submissions(request.gavel_user, campaign_id)})
    items = body_object(request).get("items")
    return Response({"data": services.ingest_submissions(request.gavel_user, campaign_id, items)}, status=202)


@api_view(["POST"])
@require_auth("administrator", "owner")
def process_submissions(request, campaign_id):
    payload = body_object(request)
    limit = payload.get("limit", 25)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise AppError(400, "INVALID_LIMIT", "Processing limit must be a whole number from 1 to 100.")
    return Response({"data": services.process_submissions(request.gavel_user, campaign_id, limit)})


@api_view(["POST"])
@require_auth("administrator", "owner")
def retry_submission(request, campaign_id, submission_id):
    return Response({"data": services.retry_submission(request.gavel_user, campaign_id, submission_id)})


@api_view(["GET"])
@require_auth("administrator", "reviewer")
def reviews(request):
    campaign_id = request.query_params.get("campaignId")
    status = request.query_params.get("status")
    return Response({"data": services.list_reviews(request.gavel_user, campaign_id, status)})


@api_view(["POST"])
@require_auth("administrator", "reviewer")
def claim_review(request, review_id):
    return Response({"data": services.claim_review(request.gavel_user, review_id)})


@api_view(["POST"])
@require_auth("administrator", "reviewer")
def release_review(request, review_id):
    return Response({"data": services.release_review(request.gavel_user, review_id)})


@api_view(["POST"])
@require_auth("administrator", "reviewer")
def submit_review(request, review_id):
    return Response({"data": services.submit_review(request.gavel_user, review_id, body_object(request))})


@api_view(["GET"])
@require_auth("administrator", "adjudicator", "owner")
def adjudications(request):
    return Response({"data": services.list_adjudications(request.gavel_user, request.query_params.get("campaignId"))})


@api_view(["POST"])
@require_auth("administrator", "adjudicator")
def resolve_adjudication(request, adjudication_id):
    return Response({"data": services.resolve_adjudication(request.gavel_user, adjudication_id, body_object(request))})


@api_view(["GET"])
@require_auth("administrator", "owner", "adjudicator")
def analytics(request):
    return Response({"data": services.analytics(request.gavel_user, request.query_params.get("campaignId"))})


@api_view(["GET"])
@require_auth("administrator", "owner", "adjudicator")
def audit(request):
    return Response({"data": services.audit_log(request.gavel_user, request.query_params.get("cursor"))})
