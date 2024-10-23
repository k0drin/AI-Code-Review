from django import forms

class RepositoryForm(forms.Form):
    url = forms.URLField(label='Repository URL', required=True)
    assignment_description = forms.CharField(label='Assignment Description', required=True, widget=forms.Textarea)
    candidate_level = forms.ChoiceField(
        label='Candidate Level',
        choices=[
            ('junior', 'Junior'),
            ('middle', 'Middle'),
            ('senior', 'Senior'),
        ],
        required=True
    )