"""Input forms for authorized moderator report actions."""

from django import forms

from apps.moderation.models import ReportStatus


class ReportTransitionForm(forms.Form):
    status = forms.ChoiceField(choices=ReportStatus.choices)
    resolution_note = forms.CharField(
        required=False,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4, "maxlength": 1000}),
    )

    def __init__(self, *args, report, **kwargs):
        super().__init__(*args, **kwargs)
        if report.status == ReportStatus.OPEN:
            choices = [ReportStatus.UNDER_REVIEW, ReportStatus.RESOLVED, ReportStatus.DISMISSED]
        elif report.status == ReportStatus.UNDER_REVIEW:
            choices = [ReportStatus.RESOLVED, ReportStatus.DISMISSED]
        else:
            choices = []
        self.fields["status"].choices = [(value, ReportStatus(value).label) for value in choices]
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["status"].widget.attrs["class"] = "form-select"

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") in {ReportStatus.RESOLVED, ReportStatus.DISMISSED} and not (
            cleaned.get("resolution_note") or ""
        ).strip():
            self.add_error("resolution_note", "A reason is required to resolve or dismiss a report.")
        return cleaned
