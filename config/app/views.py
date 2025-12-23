from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from .models import Solution, UserDetails, Issue, SiteNotification
from django.db.models import F

def vote_solution(request, solution_id, vote_type):
    """
    Handles voting logic with restrictions:
    1. Issue creator cannot vote.
    2. Users cannot vote more than once.
    """
    solution = get_object_or_404(Solution, id=solution_id)
    user_id = request.session.get('user_id')
    
    if not user_id:
        return redirect('login')
    
    user = get_object_or_404(UserDetails, id=user_id)
    
    # RULE 1: The user who created the issue cannot vote for any solution on it
    if solution.issue.reported_by_id == user:
        return redirect('issue_details', issue_id=solution.issue.id)

    # RULE 2: A person who already voted cannot vote again
    if solution.voted_by.filter(id=user.id).exists():
        return redirect('issue_details', issue_id=solution.issue.id)
    
    # NEW RULE 3: The person who suggested the SOLUTION cannot vote for their own solution
    if solution.suggested_by == user:
        # Optional: return redirect with a message
        return redirect('issue_details', issue_id=solution.issue.id)
    
    # NEW RULE: Voting must be requested by creator first
    if not solution.is_voting_enabled:
        # Prevent voting if not yet requested
        return redirect('issue_details', issue_id=solution.issue.id)
    
    if vote_type == 'upvote':
        solution.upvotes += 1
        solution.voted_by.add(user) # Record the vote
        solution.save()
        
        # Auto-resolve logic: If upvotes reach 5, approve solution and resolve issue
        if solution.upvotes >= 5:
            solution.status = 'Accepted'
            solution.save()
            
            issue = solution.issue
            issue.status = 'Resolved'
            issue.save()

            # This ensures they no longer appear in anyone's notification list
            SiteNotification.objects.filter(issue=issue).delete()
            
    elif vote_type == 'downvote':
        solution.downvotes = F('downvotes') + 1
        solution.voted_by.add(user) # Record the vote
        solution.save()
        
    return redirect('issue_details', issue_id=solution.issue.id)

def signup(request):
    template = "Signup_Form.html"
    if request.method == 'POST':
        # 1. ENSURE ALL THESE VARIABLES ARE DEFINED FIRST
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        flat_number = request.POST.get('flat_number')
        role = request.POST.get('role')
        
        # New: Get the profile picture from request.FILES
        profile_image = request.FILES.get('profile_picture')

        # 2. Check if user already exists
        if UserDetails.objects.filter(email=email).exists():
            return render(request, template, {'error': "Email already registered."})

        # 3. NOW USE THE DEFINED VARIABLES (This is where the error was occurring)
        UserDetails.objects.create(
            full_name=full_name, 
            email=email, 
            password=password, 
            flat_number=flat_number, 
            role=role,
            profile_picture=profile_image # Ensure this matches your model field
        )
        return redirect('login')
    
    return render(request, template)



def logout(request):
    request.session.flush() 
    return redirect('login')

def login(request):
    template = "Login_Form.html"
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        try:
            user = UserDetails.objects.get(email=email, password=password)
            request.session['user_id'] = user.id
            request.session.modified = True 
            return redirect('home')
        except UserDetails.DoesNotExist:
            return render(request, template, {'error': "Invalid email or password."})
    return render(request, template)

def reportIssue(request):
    template = "Raise_an_Issue_Form.html"
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        status = request.POST.get('status')
        user = UserDetails.objects.get(id=request.session.get('user_id'))
        
        new_issue = Issue.objects.create(
            title=title,
            description=description,
            status=status,
            reported_by_id=user
        )
        
        SiteNotification.objects.create(
            title="New Issue Raised",
            message=f"{title}: {description[:50]}...",
            issue=new_issue 
        )
        new_issue.save()
        return redirect('home')

    return render(request, template)

def issue_details_view(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    solutions = Solution.objects.filter(issue=issue).order_by('-upvotes', '-suggested_date')
    
    # NEW: Get the current user object to check voting status in template
    user_id = request.session.get('user_id')
    user = UserDetails.objects.filter(id=user_id).first()
    
    return render(request, 'Issue_Details_View.html', {
        'issue': issue,
        'solutions': solutions,
        'user': user  # Added this to the context
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
            
            # Fetch general data
            open_issues_count = Issue.objects.filter(status='Open', reported_by_id=user).count()
            resolved_issues_count = Issue.objects.filter(status='Resolved', reported_by_id=user).count()
            all_notifications = SiteNotification.objects.all().order_by('-id')[:10]

            # Calculate stats based on RECENT 5 issues
            recent_issues_queryset = Issue.objects.filter(reported_by_id=user).order_by('-reported_date')[:5]
            recent_issues = list(recent_issues_queryset)
            total_recent = len(recent_issues)

            if total_recent > 0:
                recent_open_count = sum(1 for i in recent_issues if i.status == 'Open')
                recent_resolved_count = sum(1 for i in recent_issues if i.status == 'Resolved')
                recent_in_review_count = sum(1 for i in recent_issues if i.status == 'In Review')

                open_pct = max(int((recent_open_count / total_recent) * 100), 1) if recent_open_count > 0 else 0
                resolved_pct = max(int((recent_resolved_count / total_recent) * 100), 1) if recent_resolved_count > 0 else 0
                in_review_pct = max(int((recent_in_review_count / total_recent) * 100), 1) if recent_in_review_count > 0 else 0
            else:
                recent_open_count = recent_resolved_count = recent_in_review_count = 0
                open_pct = resolved_pct = in_review_pct = 0

            context = {
                'user_full_name': user.full_name or user.email,
                'user_object': user,
                'open_issues_count': open_issues_count,
                'resolved_issues_count': resolved_issues_count,
                'recent_issues': recent_issues, 
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

def request_vote(request, solution_id):
    solution = get_object_or_404(Solution, id=solution_id)
    user_id = request.session.get('user_id')
    user = get_object_or_404(UserDetails, id=user_id)

    if solution.issue.reported_by_id != user or solution.issue.status == 'Resolved':
        return redirect('issue_details', issue_id=solution.issue.id)

    # UNLOCK VOTING: Set the flag to True
    solution.is_voting_enabled = True
    solution.save()

    # Create a site-wide notification
    SiteNotification.objects.create(
        title="Vote Requested!",
        message=f"The creator of '{solution.issue.title}' requests your vote for solution: {solution.title}",
        issue=solution.issue
    )
    
    # Optional: You could use Django messages to confirm the request was sent
    # messages.success(request, "Vote request notification sent to the community!")

    return redirect('issue_details', issue_id=solution.issue.id)

