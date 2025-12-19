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
        solution.upvotes = F('upvotes') + 1
    elif vote_type == 'downvote':
        # You can either decrease a total or increase a separate downvote field
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
        # Redirect back to the issue details page
        return redirect('issue_details', issue_id=issue_id)

    return render(request, 'Suggest_Solution_Form.html', {'issue': issue})

def home(request):
    user_id = request.session.get('user_id')
    if user_id:
        try:
            user = UserDetails.objects.get(id=user_id)
            open_issues_count = Issue.objects.filter(status='Open', reported_by_id=user).count()
            resolved_issues_count = Issue.objects.filter(status='Resolved', reported_by_id=user).count()
            recent_issues = Issue.objects.filter(reported_by_id=user).order_by('-reported_date')[:5]
            all_notifications = SiteNotification.objects.all().order_by('-id')[:10]

            context = {
                'user_full_name': user.full_name or user.email,
                'open_issues_count': open_issues_count,
                'resolved_issues_count': resolved_issues_count,
                'recent_issues': recent_issues,
                'notifications': all_notifications,
            }
            return render(request, 'home.html', context)
        except UserDetails.DoesNotExist:
            return redirect('login')
    return redirect('login')