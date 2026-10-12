import time
from collections import defaultdict
from datetime import datetime, timezone

from apps.shared.errors import AppError

from .. import audit, repository
from ..models import Adjudication, Campaign, ResultPublication, ReviewAssignment, Submission
from .common import (
    _ANALYTICS_TTL,
    _analytics_cache,
    _analytics_cache_exp,
    analytics_cache_key,
    current_revision,
    ensure_campaign,
    ensure_owner,
    invalidate_analytics_cache,
    iso,
    public_campaign,
)


def analytics(user, campaign_id=None):
    # Scoped cache check (per-user, per-campaign, 5s TTL, invalidated on mutations)
    _key = analytics_cache_key(user, campaign_id)
    _now = time.time()
    if _key in _analytics_cache and _now - _analytics_cache_exp.get(_key, 0) < _ANALYTICS_TTL:
        return _analytics_cache[_key]
    campaigns = list(Campaign.objects(deleted__ne=True))
    if campaign_id:
        selected = ensure_campaign(campaign_id)
        if user.role == "owner":
            ensure_owner(user, selected)
        elif user.role not in ("administrator", "adjudicator"):
            raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot access campaign analytics.")
        campaigns = [selected]
    elif user.role == "owner":
        campaigns = [row for row in campaigns if str(row.owner_id) == str(user.id)]
    campaign_ids = [row.id for row in campaigns]
    submissions = list(Submission.objects(campaign_id__in=campaign_ids)) if campaign_ids else []
    reviews = list(ReviewAssignment.objects(campaign_id__in=campaign_ids)) if campaign_ids else []
    adjudications = list(Adjudication.objects(campaign_id__in=campaign_ids)) if campaign_ids else []
    model_wins = defaultdict(int)
    resolved_pairs = 0
    for review in reviews:
        if review.status != "completed" or not review.winner_id:
            continue
        winner = repository.find_submission(str(review.winner_id))
        if winner:
            model_wins[winner.model_name] += 1
    for case in adjudications:
        if case.status == "resolved" and case.decision_id:
            winner = repository.find_submission(str(case.decision_id))
            if winner:
                model_wins[winner.model_name] += 1
            resolved_pairs += 1
    total_completed = sum(1 for row in reviews if row.status == "completed")
    pair_assignments = defaultdict(int)
    pair_votes = defaultdict(list)
    for row in reviews:
        pair_assignments[row.pair_key] += 1
        if row.status == "completed" and row.winner_id:
            pair_votes[row.pair_key].append(str(row.winner_id))
    completed_pairs = [votes for pair, votes in pair_votes.items() if len(votes) == pair_assignments[pair] and pair_assignments[pair] >= 2]
    agreement = sum(1 for votes in completed_pairs if len(set(votes)) == 1)
    campaign_breakdown = []
    for campaign in campaigns:
        campaign_assignments = defaultdict(int)
        campaign_votes = defaultdict(list)
        campaign_reviews = [row for row in reviews if row.campaign_id == campaign.id and row.status == "completed" and row.winner_id]
        for row in reviews:
            if row.campaign_id == campaign.id:
                campaign_assignments[row.pair_key] += 1
        for row in campaign_reviews:
            campaign_votes[row.pair_key].append(str(row.winner_id))
        complete_campaign_pairs = [votes for pair, votes in campaign_votes.items() if len(votes) == campaign_assignments[pair] and campaign_assignments[pair] >= 2]
        campaign_agreement = sum(1 for votes in complete_campaign_pairs if len(set(votes)) == 1)
        campaign_row = public_campaign(campaign, include_details=False)
        campaign_row["agreementRate"] = round((campaign_agreement / len(complete_campaign_pairs)) * 100) if complete_campaign_pairs else 0
        campaign_row["reviewCount"] = len(campaign_reviews)
        campaign_breakdown.append(campaign_row)
    result = {
        "campaigns": len(campaigns),
        "submissions": len(submissions),
        "processed": sum(1 for row in submissions if row.status == "ready"),
        "failed": sum(1 for row in submissions if row.status == "failed"),
        "queued": sum(1 for row in submissions if row.status in ("queued", "processing")),
        "reviewsCompleted": total_completed,
        "reviewsPending": sum(1 for row in reviews if row.status != "completed"),
        "openDisagreements": sum(1 for row in adjudications if row.status == "open"),
        "resolvedDisagreements": resolved_pairs,
        "agreementRate": round((agreement / len(completed_pairs)) * 100) if completed_pairs else 0,
        "modelWins": [{"model": name, "wins": wins} for name, wins in sorted(model_wins.items(), key=lambda row: (-row[1], row[0]))],
        "campaignBreakdown": campaign_breakdown,
    }
    # Store in scoped cache with TTL; invalidated on mutations
    _analytics_cache[_key] = result
    _analytics_cache_exp[_key] = _now
    return result


def public_publication(publication):
    return {
        "id": str(publication.id),
        "campaignId": str(publication.campaign_id),
        "revisionId": str(publication.revision_id) if publication.revision_id else None,
        "version": publication.version,
        "publishedBy": str(publication.published_by),
        "publishedAt": iso(publication.published_at),
        "snapshot": publication.snapshot,
    }


def publish_results(user, campaign_id):
    campaign = ensure_campaign(campaign_id)
    ensure_owner(user, campaign)
    if campaign.status != "completed":
        raise AppError(409, "CAMPAIGN_NOT_COMPLETE", "Complete all reviews and disagreements before publishing results.")
    latest = ResultPublication.objects(campaign_id=campaign.id).order_by("-version").first()
    version = latest.version + 1 if latest else 1
    revision = current_revision(campaign)
    publication = ResultPublication(
        campaign_id=campaign.id,
        revision_id=revision.id,
        version=version,
        snapshot=analytics(user, str(campaign.id)),
        published_by=user.id,
        published_at=datetime.now(timezone.utc),
    )
    audit.create(publication, user, "results.published", {"campaignId": str(campaign.id), "version": version})
    invalidate_analytics_cache()
    return public_publication(publication)


def get_published_results(user, campaign_id):
    campaign = ensure_campaign(campaign_id)
    if user.role == "owner":
        ensure_owner(user, campaign)
    elif user.role not in ("administrator", "adjudicator"):
        raise AppError(403, "ROLE_FORBIDDEN", "Your role cannot access published results.")
    publication = ResultPublication.objects(campaign_id=campaign.id).order_by("-version").first()
    if publication is None:
        raise AppError(404, "RESULTS_NOT_PUBLISHED", "Results have not been published for this campaign.")
    return public_publication(publication)
