from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from .models import Solution, UserDetails, Issue, SiteNotification
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count
from django.db.models import F

def vote_solution(request, solution_id, vote_type):
    solution = get_object_or_404(Solution, id=solution_id)
    
    if vote_type == 'upvote':
        # Use direct increment to check the value immediately for logic
        solution.upvotes += 1
        solution.save()
        
        # LOGIC: If upvotes reach 5, approve solution and resolve issue
        if solution.upvotes >= 5:
            solution.status = 'Accepted' # Or 'Approved'
            solution.save()
            
            issue = solution.issue
            issue.status = 'Resolved'
            issue.save()
            
    elif vote_type == 'downvote':
        solution.downvotes = F('downvotes') + 1
        solution.save()
        
    return redirect('issue_details', issue_id=solution.issue.id)

def signup(request):
    template = "Signup_Form.html"
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        flat_number = request.POST.get('flat_number')
        role = request.POST.get('role')

        if UserDetails.objects.filter(email=email).exists():
            return render(request, template, {'error': "Email already registered."})

        UserDetails.objects.create(
            full_name=full_name, email=email, password=password, 
            flat_number=flat_number, role=role
        )
        return redirect('login')
    return render(request, template)

# NEW: Logout functionality
def logout(request):
    request.session.flush() # Clears session data and logs the user out
    return redirect('login')

def login(request):
    template = "Login_Form.html"
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            # Match user by credentials
            user = UserDetails.objects.get(email=email, password=password)
            
            # FIX: Explicitly set the session and save it
            request.session['user_id'] = user.id
            request.session.modified = True 
            
            return redirect('home')
        except UserDetails.DoesNotExist:
            return render(request, template, {'error': "Invalid email or password. Please try again."})
    return render(request, template)


def reportIssue(request):
    template = "Raise_an_Issue_Form.html"
    
    if request.method == 'POST':
        # Retrieve data from the POST request
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = request.POST.get('status') # This comes from the <select> field
        
        # NOTE: You need to handle file uploads separately if you add an ImageField
        # image_file = request.FILES.get('image') 
        user_id = UserDetails.objects.get(id=request.session.get('user_id'))
        #return HttpResponse(f"request.user: {request.user}, user_id from session: {user_id}")
        # Create a new Issue instance
        new_issue = Issue.objects.create(
            title=title,
            description=description,
            status=status,
            reported_by_id= user_id #equest.user #Automatically assign the currently logged-in user
        )
         # NEW: Create a site-wide notification and link it to the new issue object
        SiteNotification.objects.create(
            title="New Issue Raised",
            message=f"{title}: {description[:50]}...",
            issue=new_issue # Link the notification directly to the Issue object
        )
        # Save the instance to the database
        new_issue.save()
        
        # Optional: Add a success message (requires Django messages framework setup)
        # messages.success(request, "Your issue has been reported successfully!")

        # Redirect the user to another page after submission (e.g., a dashboard or home)
        return redirect('home') # Use the name of your home URL pattern

    # If it's a GET request, just render the template
    return render(request, template)

def issue_details_view(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    # Fetch all solutions related to this issue
    solutions = Solution.objects.filter(issue=issue).order_by('-upvotes', '-suggested_date')
    
    return render(request, 'Issue_Details_View.html', {
        'issue': issue,
        'solutions': solutions # Pass solutions to the template
    })


def suggest_solution(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        user_id = request.session.get('user_id')
        user = get_object_or_404(UserDetails, id=user_id)

        Solution.objects.create(
            title=title,
            description=description,
            issue=issue,
            suggested_by=user,
        )
        
        # LOGIC: If a solution is added, change issue status to 'In Review'
        if issue.status == 'Open':
            issue.status = 'In Review'
            issue.save()

        return redirect('issue_details', issue_id=issue_id)

    return render(request, 'Suggest_Solution_Form.html', {'issue': issue})

def home(request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = UserDetails.objects.get(id=user_id)
            
            # Use general counts for reference (as before, but will use new vars in template)
            open_issues_count = Issue.objects.filter(status='Open', reported_by_id=user).count()
            resolved_issues_count = Issue.objects.filter(status='Resolved', reported_by_id=user).count()
            all_notifications = SiteNotification.objects.all().order_by('-id')[:10]

            # NEW LOGIC: Calculate counts and percentages based ONLY on the recent 5 issues for the cards
            recent_issues_queryset = Issue.objects.filter(reported_by_id=user).order_by('-reported_date')[:5]
            recent_issues = list(recent_issues_queryset) # Convert to list to use Python logic

            total_recent = len(recent_issues)
            # Avoid division by zero if the user has no issues
            if total_recent > 0:
                recent_open_count = sum(1 for i in recent_issues if i.status == 'Open')
                recent_resolved_count = sum(1 for i in recent_issues if i.status == 'Resolved')
                recent_in_review_count = sum(1 for i in recent_issues if i.status == 'In Review') # Matches the 'Pending Votes' idea from image

                # Calculate percentage widths for progress bars (as integer for CSS width style)
                # Use max(..., 1) to ensure a visible bar even with a tiny percentage
                open_pct = max(int((recent_open_count / total_recent) * 100), 1) if recent_open_count > 0 else 0
                resolved_pct = max(int((recent_resolved_count / total_recent) * 100), 1) if recent_resolved_count > 0 else 0
                in_review_pct = max(int((recent_in_review_count / total_recent) * 100), 1) if recent_in_review_count > 0 else 0
            else:
                recent_open_count, recent_resolved_count, recent_in_review_count = 0, 0, 0
                open_pct, resolved_pct, in_review_pct = 0, 0, 0
            
            context = {
                'user_full_name': user.full_name or user.email,
                # Old Context (kept for clarity but new vars used in cards)
                'open_issues_count': open_issues_count,
                'resolved_issues_count': resolved_issues_count,
                # New Context for Summary Cards (based on recent 5 issues)
                'recent_issues': recent_issues, # The list used for the table
                'card_open_count': recent_open_count,
                'card_resolved_count': recent_resolved_count,
                'card_pending_count': recent_in_review_count,
                'card_open_pct': open_pct,
                'card_resolved_pct': resolved_pct,
                'card_pending_pct': in_review_pct,
                'notifications': all_notifications,
            }
            return render(request, 'home.html', context)
        except UserDetails.DoesNotExist:
            return redirect('login')
    return redirect('login')