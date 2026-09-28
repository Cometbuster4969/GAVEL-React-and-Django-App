from django.urls import path

from . import views

urlpatterns = [
    path("auth/login", views.login),
    path("auth/me", views.me),
    path("campaigns", views.campaigns),
    path("campaigns/", views.campaigns),
    path("campaigns/create", views.create_campaign),
    path("campaigns/<str:campaign_id>/versions", views.create_campaign_version),
    path("campaigns/<str:campaign_id>/transition", views.campaign_transition),
    path("campaigns/<str:campaign_id>/publish-results", views.publish_results),
    path("campaigns/<str:campaign_id>/published-results", views.published_results),
    path("campaigns/<str:campaign_id>/results-export", views.export_results),
    path("campaigns/<str:campaign_id>/submissions/process", views.process_submissions),
    path("campaigns/<str:campaign_id>/submissions/<str:submission_id>/retry", views.retry_submission),
    path("campaigns/<str:campaign_id>/submissions", views.campaign_submissions),
    path("campaigns/<str:campaign_id>", views.campaign_detail),
    path("reviews", views.reviews),
    path("reviews/<str:review_id>/claim", views.claim_review),
    path("reviews/<str:review_id>/release", views.release_review),
    path("reviews/<str:review_id>/submit", views.submit_review),
    path("adjudications", views.adjudications),
    path("adjudications/<str:adjudication_id>/resolve", views.resolve_adjudication),
    path("analytics", views.analytics),
    path("audit", views.audit),
]
