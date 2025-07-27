

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator

class User(AbstractUser):
    ROLES = (
        ('AR', 'Automation Realization'),
        ('DM', 'Delivery Manager'),
        ('OM', 'Operations Manager'),
    )
    role = models.CharField(max_length=2, choices=ROLES)
    
    def is_ar(self):
        return self.role == 'AR'
    
    def is_dm(self):
        return self.role == 'DM'
    
    def is_om(self):
        return self.role == 'OM'

class ClaimStatus(models.Model):
    consumer_no = models.CharField(max_length=100)
    consumer_name = models.CharField(max_length=255)
    eme = models.FloatField(null=True, blank=True)
    justification_text = models.TextField(blank=True)
    justification_file = models.FileField(
        upload_to='justifications/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'])]
    )
    approved_by_dm = models.BooleanField(default=False)
    approved_by_om = models.BooleanField(default=False)
    approved_by_ar = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='submitted_claims')
    STATUS_CHOICES = (
        ('new', 'New'),
        ('dm_review', 'DM Review Requested'),
        ('dm_approved', 'DM Approved'),
        ('om_review', 'OM Review Requested'),
        ('ar_review', 'AR Review'),
        ('om_approved', 'OM Approved'),
        ('ar_approved', 'AR Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    )
    def get_absolute_url(self):
        return reverse('view_claim', args=[str(self.id)])
    
    @property
    def justification_preview(self):
        if self.justification_text:
            return self.justification_text[:50] + "..." if len(self.justification_text) > 50 else self.justification_text
        return "No justification text"
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    current_handler = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='handled_claims')
    def save(self, *args, **kwargs):
    # Update status based on approvals - MODIFIED VERSION
       if self.is_fully_approved():
        self.status = 'approved'
       elif self.approved_by_ar:
        self.status = 'ar_approved'
       elif self.approved_by_om:
        self.status = 'om_approved'
       elif self.approved_by_dm:
        self.status = 'dm_approved'
    # Don't automatically set status to 'new' here
    
       super().save(*args, **kwargs)  # This MUST be at the end
    
    
    
    def is_fully_approved(self):
        return self.approved_by_dm and self.approved_by_om and self.approved_by_ar
    
    def __str__(self):
        return f"{self.consumer_no} - {self.consumer_name}"

class EMEFinal(models.Model):
    consumer_no = models.CharField(max_length=100)
    consumer_name = models.CharField(max_length=255)
    eme = models.FloatField()
    justification_text = models.TextField()
    justification_file = models.FileField(upload_to='final_justifications/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.consumer_no} - {self.consumer_name} (EME: {self.eme})"

class CommunicationLog(models.Model):
    claim = models.ForeignKey(ClaimStatus, on_delete=models.CASCADE, related_name='communications')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='received_messages')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(upload_to='communication_attachments/', blank=True, null=True)
    
    def __str__(self):
        return f"Communication for {self.claim} at {self.timestamp}"
    
