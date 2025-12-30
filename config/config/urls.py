"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include   
from app import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.signup, name='signup'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('home/', views.home, name='home'),
    path('report-issue/', views.reportIssue, name='report-issue'),
    path('issue/<str:issue_id>/', views.issue_details_view, name='issue_details'),
    path('issue/<str:issue_id>/suggest-solution/', views.suggest_solution, name='suggest_solution'),
    path('solution/<int:solution_id>/vote/<str:vote_type>/', views.vote_solution, name='vote_solution'),
    path('solution/<int:solution_id>/request-vote/', views.request_vote, name='request_vote'),
    path("chatbot/", views.chatbot, name='chatbot'),  # Include chatbot app URLs
    path('chat_api/', views.chat_api, name='chat_api'),
    path('admin/', admin.site.urls),
]

# Only add this during development (DEBUG=True in settings.py)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
