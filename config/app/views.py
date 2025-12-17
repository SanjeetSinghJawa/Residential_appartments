from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from .models import user_details, Issue
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count

def signup(request):

    template= "Signup_Form.html"
    if request.method == 'POST':
        
        email = request.POST.get('email')
        password = request.POST.get('password')
        flat_number = request.POST.get('flat_number')
        role = request.POST.get('flat_number')

       
        create_user = user_details.objects.create(email=email, password=password, flat_number=flat_number, role=role)
        create_user.save()
        return HttpResponse("User created successfully")
    return render(request, template)

def login(request):
    template= "Login_Form.html"
    if request.method == 'POST':
        
        email = request.POST.get('email')
        password = request.POST.get('password')
        try:
            user = user_details.objects.get(email=email, password=password)
            return redirect('home')
        except user_details.DoesNotExist:
            return HttpResponse("Invalid credentials")
    return render(request, template)

def reportIssue(request):
    template= "Raise_an_Issue_Form.html"
    return render(request, template) 

@login_required
def home(request):
    user = request.user
    
    # Calculate summary statistics
    open_issues_count = Issue.objects.filter(status='Open').count()
    resolved_issues_count = Issue.objects.filter(status='Resolved').count()
    # Placeholder for pending votes count (requires a separate Voting model)
    pending_votes_count = 3 # Static placeholder for now

    # Get recent issues to display in the table
    recent_issues = Issue.objects.order_by('-reported_date')[:5] # Get last 5

    context = {
        'user_full_name': user.get_full_name() or user.username,
        'open_issues_count': open_issues_count,
        'resolved_issues_count': resolved_issues_count,
        'pending_votes_count': pending_votes_count,
        'recent_issues': recent_issues,
    }
    return render(request, 'home.html', context)