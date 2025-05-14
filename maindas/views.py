from django.shortcuts import render


def display_main_dashboard(request):
    return render(request, 'maindas/dashboard.html', {})
