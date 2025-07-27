from django import forms
from .models import ClaimStatus, CommunicationLog
from django.core.validators import FileExtensionValidator
from django.db.models.functions import ExtractYear, ExtractMonth


class DashboardFilterForm(forms.Form):
    YEAR_CHOICES = [(None, 'All Years')] + [(year, year) for year in 
                   ClaimStatus.objects.annotate(year=ExtractYear('created_at'))
                   .values_list('year', flat=True).distinct().order_by('-year')]
    
    MONTH_CHOICES = [(None, 'All Months')] + [(i, month) for i, month in 
                    enumerate(['January', 'February', 'March', 'April', 'May', 'June',
                             'July', 'August', 'September', 'October', 'November', 'December'], 1)]
    
    year = forms.ChoiceField(choices=YEAR_CHOICES, required=False)
    month = forms.ChoiceField(choices=MONTH_CHOICES, required=False)
    consumer_name = forms.CharField(required=False)
    consumer_no = forms.CharField(required=False)

class JustificationForm(forms.ModelForm):
    class Meta:
        model = ClaimStatus
        fields = ['eme', 'justification_text', 'justification_file']
        widgets = {
            'justification_text': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean_eme(self):
        eme = self.cleaned_data.get('eme')
        if eme is not None and eme < 0:
            raise forms.ValidationError("EME cannot be negative")
        return eme

class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label='Select Excel File',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])],
        help_text="File must contain columns: consumer_no, consumer_name, eme"
    )
class ClaimStatusForm(forms.ModelForm):
    class Meta:
        model = ClaimStatus
        fields = ['eme', 'justification_text', 'justification_file']
        widgets = {
            'justification_text': forms.Textarea(attrs={'rows': 4}),
        }

class ApprovalForm(forms.Form):
    approve = forms.BooleanField(
        required=False,
        label='Approve this claim',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    comments = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter any additional comments...'
        })
    )

class CommunicationForm(forms.ModelForm):
    class Meta:
        model = CommunicationLog
        fields = ['message', 'attachment']
        widgets = {
            'message': forms.Textarea(attrs={'rows': 3}),
        }

class DMApprovalForm(forms.ModelForm):
    justification_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=True,
        help_text="Please provide detailed justification for the EME value"
    )
    
    justification_file = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'png']
        )],
        help_text="Upload supporting documents (PDF, Word, Excel, or images)"
    )
    
    class Meta:
        model = ClaimStatus
        fields = ['eme', 'justification_text', 'justification_file']
        
    def clean_eme(self):
        eme = self.cleaned_data['eme']
        if eme is not None and eme < 0:
            raise forms.ValidationError("EME value cannot be negative")
        return eme