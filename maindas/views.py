from django.shortcuts import render
# Create your views here.


def display_main_dashboard(request):
    return render(request, 'maindas/dashboard.html', {})
