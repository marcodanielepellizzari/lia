"""
HTML pages for the review panel (slide 7): the Reviewer receives the
merge request, checks the new anagraphical values found during import,
adds notes, and approves/rejects.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import ListView

from accounts.mixins import ReviewerRequiredMixin
from .forms import MergeRequestReviewForm
from .models import MergeRequest, DatasetStatus, DatasetVisibility


class MergeRequestListView(ReviewerRequiredMixin, ListView):
    model = MergeRequest
    template_name = "workflow/merge_request_list.html"
    context_object_name = "merge_requests"

    def get_queryset(self):
        return MergeRequest.objects.select_related("dataset", "submitted_by").order_by(
            "status", "-created_at"
        )


from django.contrib.auth.decorators import login_required, user_passes_test  # noqa: E402


def _is_reviewer(user):
    return user.is_authenticated and user.is_reviewer


@login_required
@user_passes_test(_is_reviewer, login_url="login")
def merge_request_detail(request, pk):
    merge_request = get_object_or_404(
        MergeRequest.objects.select_related("dataset", "submitted_by", "dataset__owner"), pk=pk
    )

    if request.method == "POST":
        form = MergeRequestReviewForm(request.POST, instance=merge_request)
        action = request.POST.get("action")
        if merge_request.status != MergeRequest.Status.OPEN:
            messages.error(request, "This merge request has already been closed.")
            return redirect("merge-request-detail", pk=pk)

        if form.is_valid():
            merge_request = form.save(commit=False)
            merge_request.reviewer = request.user
            merge_request.reviewed_at = timezone.now()

            if action == "approve":
                merge_request.status = MergeRequest.Status.APPROVED
                merge_request.dataset.status = DatasetStatus.MERGED
                merge_request.dataset.visibility = DatasetVisibility.PUBLIC
                merge_request.dataset.save(update_fields=["status", "visibility"])
                messages.success(request, f"Dataset '{merge_request.dataset.name}' approved and published.")
            elif action == "reject":
                merge_request.status = MergeRequest.Status.REJECTED
                merge_request.dataset.status = DatasetStatus.REJECTED
                merge_request.dataset.save(update_fields=["status"])
                messages.warning(request, f"Dataset '{merge_request.dataset.name}' rejected.")
            else:
                messages.error(request, "Invalid action.")
                return redirect("merge-request-detail", pk=pk)

            merge_request.save()
            return redirect("merge-request-list")
    else:
        form = MergeRequestReviewForm(instance=merge_request)

    return render(request, "workflow/merge_request_detail.html", {
        "merge_request": merge_request, "form": form,
        "sample_count": merge_request.dataset.samples.count(),
    })
