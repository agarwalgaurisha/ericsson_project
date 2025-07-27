


import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse, FileResponse
from .models import ClaimStatus, EMEFinal, User, CommunicationLog
from .forms import ExcelUploadForm, ClaimStatusForm, ApprovalForm, CommunicationForm, DMApprovalForm


def role_check(user, role):
    return user.role == role

@login_required
@user_passes_test(lambda u: u.role == 'AR')
def ar_approve(request, claim_id):
    claim = get_object_or_404(ClaimStatus, id=claim_id)
    
    if request.method == 'POST':
        claim.approved_by_ar = True
        claim.status = 'ar_approved'
        claim.save()
        
        messages.success(request, 'Claim approved by AR successfully!')
        return redirect('ar_dashboard')
    
    return render(request, 'eme/ar_approve.html', {
        'claim': claim
    })
@login_required
def home(request):
    if request.user.is_ar():
        return redirect('ar_dashboard')
    elif request.user.is_dm():
        return redirect('dm_dashboard')
    elif request.user.is_om():
        return redirect('om_dashboard')
    return redirect('login')

# AR Views
@login_required
@user_passes_test(lambda u: role_check(u, 'AR'))
def ar_dashboard(request):
    claims = ClaimStatus.objects.all()
    final_approvals = EMEFinal.objects.all()
    return render(request, 'eme/ar_dashboard.html', {
        'claims': claims,
        'final_approvals': final_approvals
    })

@login_required
@user_passes_test(lambda u: role_check(u, 'AR'))
def upload_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                df = pd.read_excel(request.FILES['excel_file'])
                
                # Validate required columns
                required_columns = ['consumer_no', 'consumer_name', 'eme']
                if not all(col in df.columns for col in required_columns):
                    messages.error(request, "Excel file must contain 'consumer_no', 'consumer_name', and 'eme' columns")
                    return redirect('upload_excel')
                
                # Convert EME to numeric, handling errors
                df['eme'] = pd.to_numeric(df['eme'], errors='coerce')
                
                # Filter records
                filtered_df = df[(df['eme'].isna()) | (df['eme'] == 0) | (df['eme'] > 1)]
                
                # Create records in bulk for better performance
                records = [
                    ClaimStatus(
                        consumer_no=row['consumer_no'],
                        consumer_name=row['consumer_name'],
                        eme=row['eme'] if not pd.isna(row['eme']) else None,
                        submitted_by=request.user
                    )
                    for _, row in filtered_df.iterrows()
                ]
                
                ClaimStatus.objects.bulk_create(records)
                messages.success(request, f"Successfully processed {len(records)} records")
                return redirect('ar_dashboard')
                
            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = ExcelUploadForm()
    
    return render(request, 'eme/upload_excel.html', {'form': form})

@login_required
@user_passes_test(lambda u: role_check(u, 'DM'))
def dm_approve(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            # Update approval status
            claim.approved_by_dm = form.cleaned_data['approve']
            claim.justification_text = form.cleaned_data.get('comments', '')
            claim.save()
            
            # Add communication log if comments exist
            if form.cleaned_data['comments']:
                CommunicationLog.objects.create(
                    claim=claim,
                    sender=request.user,
                    receiver=User.objects.filter(role='AR').first(),
                    message=form.cleaned_data['comments']
                )
            
            messages.success(request, 'Decision submitted successfully!')
            return redirect('dm_dashboard')
    else:
        form = ApprovalForm()
    
    return render(request, 'eme/approve_claim.html', {
        'form': form,
        'claim': claim,
        'approval_type': 'DM'
    })
@login_required
@user_passes_test(lambda u: role_check(u, 'AR'))
def request_dm_review(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    # Get all DMs, not just first one
    dms = User.objects.filter(role='DM')
    if not dms.exists():
        messages.error(request, "No DM users found in the system")
        return redirect('ar_dashboard')
    # Prevent resending already sent claims
    if claim.status != 'new':  # Assuming 'new' is initial status
        messages.warning(request, "Claim already sent for review")
        return redirect('ar_dashboard')
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST, request.FILES)
        if form.is_valid():
            # Update claim status
            claim.status = 'dm_review'
            claim.current_handler = dms.first() 
            # or assign to specific DM
            claim.save()
            
            # Create communication log for each DM
            for dm in dms:
                CommunicationLog.objects.create(
                    claim=claim,
                    sender=request.user,
                    receiver=dm,
                    message=form.cleaned_data['message'],
                    attachment=form.cleaned_data.get('attachment')
                )
                
                # Send email notification to each DM
                try:
                    send_mail(
                        f'EME Update Request - {claim.consumer_no}',
                        f'A new EME update request has been submitted for consumer {claim.consumer_name} ({claim.consumer_no}).\n\n'
                        f'Message: {form.cleaned_data["message"]}\n\n'
                        f'Please log in to review this request.',
                        settings.DEFAULT_FROM_EMAIL,
                        [dm.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    messages.warning(request, f"Email notification to {dm.email} failed: {str(e)}")
            
            messages.success(request, 'Request sent to DM(s) successfully!')
            return redirect('ar_dashboard')
    else:
        initial_message = (
            f"Please review this claim for consumer {claim.consumer_name} ({claim.consumer_no}).\n"
            f"Current EME value: {claim.eme or 'Not set'}"
        )
        form = CommunicationForm(initial={'message': initial_message})
    
    context = {
        'title': 'Send to DM for Review',
        'message': 'You are about to send this claim to the Delivery Manager for review.',
        'form': form,
        'action_url': request.path,
        'claim': claim,
    }
    return render(request, 'eme/confirm_action.html', context)
@login_required
@user_passes_test(lambda u: role_check(u, 'AR'))
def final_approve(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    if not (claim.approved_by_dm and claim.approved_by_om):
        messages.error(request, 'Claim must be approved by both DM and OM first!')
        return redirect('ar_dashboard')
    
    # Move to EMEFinal
    EMEFinal.objects.create(
        consumer_no=claim.consumer_no,
        consumer_name=claim.consumer_name,
        eme=claim.eme,
        justification_text=claim.justification_text,
        justification_file=claim.justification_file,
        approved_by=request.user
    )
    
    # Delete from ClaimStatus
    claim.delete()
    
    messages.success(request, 'Claim approved and moved to final records!')
    return redirect('ar_dashboard')

# DM Views
@login_required
@user_passes_test(lambda u: role_check(u, 'DM'))
def dm_dashboard(request):
    
    pending_claims = ClaimStatus.objects.filter(
        approved_by_dm=False,
        status='dm_review',

        
    ).order_by('-created_at')
    
    approved_claims = ClaimStatus.objects.filter(
        approved_by_dm=True,
        
    ).order_by('-updated_at')[:10]
    
    return render(request, 'eme/dm_dashboard.html', {
        'pending_claims': pending_claims,
        'approved_claims': approved_claims,
        'claims': pending_claims 
    })

@login_required
@user_passes_test(lambda u: role_check(u, 'DM'))
def edit_claim(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    if request.method == 'POST':
        form = ClaimStatusForm(request.POST, request.FILES, instance=claim)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.approved_by_dm = True  # Auto-approve when DM saves
            claim.save()
            messages.success(request, 'Claim updated and approved successfully!')
            return redirect('dm_dashboard')
    else:
        form = ClaimStatusForm(instance=claim)
    
    return render(request, 'eme/edit_claim.html', {
        'form': form,
        'claim': claim
    })

@login_required
@user_passes_test(lambda u: role_check(u, 'DM'))
def request_om_approval(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    if not claim.approved_by_dm:
        messages.error(request, "You must approve this claim before requesting OM approval")
        return redirect('dm_dashboard')
    
    om = User.objects.filter(role='OM').first()
    if not om:
        messages.error(request, "No OM user found in the system")
        return redirect('dm_dashboard')
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST, request.FILES)
        if form.is_valid():
            # Create communication log
            CommunicationLog.objects.create(
                claim=claim,
                sender=request.user,
                receiver=om,
                message=form.cleaned_data['message'],
                attachment=form.cleaned_data.get('attachment')
            )
            
            # Send email notification
            try:
                send_mail(
                    f'OM Approval Requested for Claim {claim.consumer_no}',
                    f'DM {request.user.username} has requested your approval for claim {claim.consumer_no}.\n\n'
                    f'Message: {form.cleaned_data["message"]}',
                    settings.DEFAULT_FROM_EMAIL,
                    [om.email],
                    fail_silently=True
                )
            except Exception as e:
                messages.warning(request, f"Email notification failed: {str(e)}")
            
            messages.success(request, "OM approval request sent successfully!")
            return redirect('dm_dashboard')
    else:
        form = CommunicationForm()
    
    return render(request, 'eme/request_om_approval.html', {
        'form': form,
        'claim': claim
    })

# OM Views
@login_required
@user_passes_test(lambda u: role_check(u, 'OM'))
def om_dashboard(request):
    claims = ClaimStatus.objects.filter(
        approved_by_dm=True,
        approved_by_om=False
    )
    
    processed_claims = ClaimStatus.objects.filter(
        approved_by_om=True
    ).order_by('-updated_at')[:10]
    
    return render(request, 'eme/om_dashboard.html', {
        'claims': claims,
        'processed_claims': processed_claims
    })

@login_required
@user_passes_test(lambda u: role_check(u, 'OM'))
def om_approve(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    if not claim.approved_by_dm:
        messages.error(request, "This claim hasn't been approved by DM yet")
        return redirect('om_dashboard')
    
    if request.method == 'POST':
        form = ApprovalForm(request.POST)
        if form.is_valid():
            claim.approved_by_om = form.cleaned_data['approve']
            claim.save()
            
            # Create communication log if comments exist
            if form.cleaned_data['comments']:
                CommunicationLog.objects.create(
                    claim=claim,
                    sender=request.user,
                    receiver=User.objects.filter(role='AR').first(),
                    message=form.cleaned_data['comments']
                )
            
            messages.success(request, 'Approval status updated!')
            return redirect('om_dashboard')
    else:
        form = ApprovalForm()
    
    return render(request, 'eme/approve_claim.html', {
        'form': form,
        'claim': claim
    })

# Common Views
@login_required
def view_justification(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    if claim.justification_file:
        return FileResponse(open(claim.justification_file.path, 'rb'))
    return HttpResponse("No justification file available.")

@login_required
def view_communications(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    communications = claim.communications.all().order_by('-timestamp')
    return render(request, 'eme/communications.html', {
        'claim': claim,
        'communications': communications
    })

@login_required
def add_communication(request, claim_id):
    claim = get_object_or_404(ClaimStatus, pk=claim_id)
    
    if request.method == 'POST':
        form = CommunicationForm(request.POST, request.FILES)
        if form.is_valid():
            communication = form.save(commit=False)
            communication.claim = claim
            communication.sender = request.user
            
            # Determine receiver based on current user role
            if request.user.is_ar():
                communication.receiver = User.objects.filter(role='DM').first()
            elif request.user.is_dm():
                communication.receiver = User.objects.filter(role='OM').first()
            elif request.user.is_om():
                communication.receiver = User.objects.filter(role='AR').first()
            
            communication.save()
            messages.success(request, 'Message sent successfully!')
            return redirect('view_communications', claim_id=claim.id)
    else:
        form = CommunicationForm()
    
    return render(request, 'eme/add_communication.html', {
        'form': form,
        'claim': claim
    })

def view_claim_details(request, claim_id):
    claim = get_object_or_404(ClaimStatus, id=claim_id)
    context = {
        'claim': claim,
    }
    return render(request, 'eme/claim_details.html', context)

@login_required
@user_passes_test(lambda u: u.role == 'DM')
def dm_approve_record(request, claim_id):
    claim = get_object_or_404(ClaimStatus, id=claim_id)
    
    if request.method == 'POST':
        form = DMApprovalForm(request.POST, request.FILES, instance=claim)
        if form.is_valid():
            claim = form.save(commit=False)
            claim.approved_by_dm = True
            claim.status = 'dm_approved'  # If you have status field
            claim.save()
            
            messages.success(request, 'Record updated and approved by DM.')
            return redirect('dm_dashboard')
    else:
        form = DMApprovalForm(instance=claim)
    
    return render(request, 'eme/dm_approve.html', {
        'form': form,
        'claim': claim
    })