from django.shortcuts import render

# Create your views here.
def table_index(request):
    return render(request, 'designapps/table_index_two.html')