from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # AR URLs
    path('ar/', views.ar_dashboard, name='ar_dashboard'),
    path('ar/upload/', views.upload_excel, name='upload_excel'),
    path('ar/request-review/<int:claim_id>/', views.request_dm_review, name='request_dm_review'),
    
    path('ar/final-approve/<int:claim_id>/', views.final_approve, name='final_approve'),
    path('ar/approve/<int:claim_id>/', views.ar_approve, name='ar_approve'),
    
    # DM URLs
    path('dm/', views.dm_dashboard, name='dm_dashboard'),
    path('dm/edit/<int:claim_id>/', views.edit_claim, name='edit_claim'),

    path('dm/approve/<int:claim_id>/', views.dm_approve_record, name='dm_approve'),
    
    path('dm/', views.dm_dashboard, name='dm_dashboard'),

    # OM URLs
    path('om/', views.om_dashboard, name='om_dashboard'),
    path('om/approve/<int:claim_id>/', views.om_approve, name='om_approve'),
    
    # Common URLs
    path('justification/<int:claim_id>/', views.view_justification, name='view_justification'),
    path('communications/<int:claim_id>/', views.view_communications, name='view_communications'),
    path('add-communication/<int:claim_id>/', views.add_communication, name='add_communication'),
    path('dm/request-om/<int:claim_id>/', views.request_om_approval, name='request_om_approval'),
    path('claim/<int:claim_id>/', views.view_claim_details, name='view_claim_details'),
]