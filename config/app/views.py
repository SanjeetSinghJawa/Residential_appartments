from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from django.shortcuts import redirect
from .models import UserDetails, Issue, SiteNotification
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

       
        create_user = UserDetails.objects.create(email=email, password=password, flat_number=flat_number, role=role)
        create_user.save()
        return HttpResponse("User created successfully")
    return render(request, template)

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
            return HttpResponse("Invalid credentials")
    return render(request, template)

@login_required
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
        # *NEW*: Create a site-wide notification for the new issue
        SiteNotification.objects.create(
            title="New Issue Raised",
            message=f"{title}: {description[:50]}..."
        )
        # Save the instance to the database
        new_issue.save()
        
        # Optional: Add a success message (requires Django messages framework setup)
        # messages.success(request, "Your issue has been reported successfully!")

        # Redirect the user to another page after submission (e.g., a dashboard or home)
        return redirect('home') # Use the name of your home URL pattern

    # If it's a GET request, just render the template
    return render(request, template)

@login_required
def home(request):
    user_id = request.session.get('user_id')
    
    if user_id:
        try:
            # Fetch the user details using the ID from the session
            user = UserDetails.objects.get(id=user_id)
    
            # Calculate summary statistics
            open_issues_count = Issue.objects.filter(status='Open').filter(reported_by_id=user).count()
            resolved_issues_count = Issue.objects.filter(status='Resolved').filter(reported_by_id=user).count()
            pending_votes_count = 3 # Static placeholder for now

            # Get recent issues to display in the table
            #recent_issues = Issue.objects.order_by('-reported_date')[:5] # Get last 5
            recent_issues = Issue.objects.filter(reported_by_id=user)

            # *NEW*: Fetch all notifications
            all_notifications = SiteNotification.objects.all()[:10] # Get recent 10

            context = {
                'user_full_name': user.email,  # Assuming email as identifier
                'open_issues_count': open_issues_count,
                'resolved_issues_count': resolved_issues_count,
                'pending_votes_count': pending_votes_count,
                'recent_issues': recent_issues,
                'notifications': all_notifications, # Add to context
            }
            return render(request, 'home.html', context)
        except UserDetails.DoesNotExist:
            return redirect('login')
    else:
        # If no user_id in session, the user is not "logged in"
        return redirect('login')