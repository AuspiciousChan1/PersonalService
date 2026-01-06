from django.shortcuts import render


def index(request):
    """Homepage view"""
    return render(request, 'index.html')
