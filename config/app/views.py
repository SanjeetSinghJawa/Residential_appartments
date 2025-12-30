from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponse
from .models import Solution, UserDetails, Issue, SiteNotification
from django.db.models import F
from django.http import JsonResponse
from chatbot.utils import simple_chatbot_view

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from openai import OpenAI
import json
from django.conf import settings

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist


client = OpenAI(api_key=settings.OPEN_API_KEY)

@receiver(post_save, sender=Issue)
def ai_suggest_solution(sender, instance, created, **kwargs):
    if created:
        try:
            # 1. Get the AI User (Make sure this email exists in your UserDetails table!)
            ai_user = UserDetails.objects.get(email="ai_assistant@apartment.com")

            # 2. Call OpenAI for a suggested solution
            # Crafted a better prompt for more specific results
            prompt = f"Provide one concise, practical solution for the following apartment maintenance issue title: '{instance.title}'. Description: '{instance.description}'"
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages="pipe is leaking"
            )
            ai_reply = response.choices[0].message.content.strip() # Strip whitespace/newlines

            # 3. Create the Solution automatically
            Solution.objects.create(
                title=f"AI-Generated Solution",
                description=ai_reply,
                issue=instance,
                suggested_by=ai_user,
                status='Pending',
                is_ai_generated=True # **CRITICAL: Set the new field to True**
            )
            
            # 4. Update Issue status to 'In Review' as per your flow
            instance.status = 'In Review'
            instance.save()
            print(f"AI successfully suggested a solution for Issue ID {instance.id}")

        except ObjectDoesNotExist:
            print("ERROR: AI User profile not found in UserDetails. Please create a user with email 'ai_assistant@apartment.com'.")
        except Exception as e:
            # Catch other potential errors like API connection issues
            print(f"AI Suggestion failed due to API error: {str(e)}")
            

def chat_api(request):
    if request.method == "POST":
        user_message = request.POST.get("message")
        
        try:
            # Call OpenAI SDK (2025 version)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": user_message}]
            )
            bot_reply = response.choices[0].message.content
            
            # Return JSON instead of rendering a template
            return JsonResponse({
                'status': 'success',
                'reply': bot_reply
            })
            
        except Exception as e:
            # Return JSON error so the JavaScript can handle it
            return JsonResponse({
                'status': 'error',
                'reply': f"I'm having trouble connecting right now. ({str(e)})"
            }, status=500)

    # If someone tries to access via GET, return an error or redirect
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=400)

def chatbot(request):
    if request.method == 'POST':
        user_message = request.POST.get('message', '')
        bot_response = simple_chatbot_view(user_message)
        return JsonResponse({'response': bot_response})
    return render(request, 'chatbot.html')

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
    
    # 1. Check if AI solutions already exist
    ai_exists = Solution.objects.filter(issue=issue, is_ai=True).exists()

    if not ai_exists:
        try:
            prompt = (
                f"Suggest 1 solution for: {issue.title}. Description: {issue.description}. "
                "Return ONLY a JSON list with: 'title', 'description', 'confidence' (0-100)."
            )
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={ "type": "json_object" },
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw_content = response.choices[0].message.content
            data = json.loads(raw_content)
            
            # Extract list safely: handles {"solutions": [...]} or just [...]
            new_solutions_list = data.get("solutions") if isinstance(data, dict) and "solutions" in data else data
            if isinstance(new_solutions_list, dict): # Handle case where it's a single object
                new_solutions_list = [new_solutions_list]

            for item in new_solutions_list:
                raw_conf = item.get('confidence', 0)
                # Map strings if AI ignores "integer" instruction
                mapping = {"High": 90, "Medium": 50, "Low": 20}
                processed_conf = mapping.get(raw_conf, raw_conf) if isinstance(raw_conf, str) else raw_conf

                # CRITICAL: Create the object in the DB
                Solution.objects.create(
                    issue=issue,
                    title=item.get('title', 'AI Suggestion'),
                    description=item.get('description', ''),
                    confidence=processed_conf,
                    is_ai=True,
                    suggested_by=None
                )
        except Exception as e:
            print(f"ERROR [AI Generation]: {str(e)}")

    # 2. Query ALL solutions ONLY AFTER the generation logic is done
    all_solutions = Solution.objects.filter(issue=issue).order_by('-is_ai', '-upvotes')

    user_id = request.session.get('user_id')
    user = UserDetails.objects.filter(id=user_id).first()
    
    return render(request, 'Issue_Details_View.html', {
        'issue': issue,
        'solutions': all_solutions,
        'user': user,
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

    # 1. Safety check: Only creator can request, and only if not already resolved
    if solution.issue.reported_by_id != user or solution.issue.status == 'Resolved':
        return redirect('issue_details', issue_id=solution.issue.id)

    # UNLOCK VOTING: Set the flag to True
    # 2. NEW: Only send notification if voting was NOT already enabled
    if not solution.is_voting_enabled:
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

