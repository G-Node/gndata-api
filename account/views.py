from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login

from account.forms import SignUpForm


def signup(request):

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            username, password = form.save()
            novice = authenticate(username=username, password=password)
            login(request, novice)
            return HttpResponseRedirect("/document/")
    else:
        form = SignUpForm()

    return render(request, "account/signup.html", {'form': form})