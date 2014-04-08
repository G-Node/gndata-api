from django.shortcuts import render, render_to_response
from django.contrib.auth.forms import UserCreationForm

def signup(request):
    if request.method =='POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(form.cleaned_data['username'], None, form.cleaned_data['password1'])
            user.save()
            return render_to_response('QCM/index.html')  # Redirect after POST
    else:
        form = UserCreationForm()  # An unbound form

    return render_to_response('register.html', {
            'form': form,
        },context_instance=RequestContext(request))