from django.shortcuts import render
from django.http import HttpResponseRedirect
from account.forms import SignUpForm


def signup(request):

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            return HttpResponseRedirect("/account/login")
    else:
        form = SignUpForm()

    return render(request, "account/signup.html", {'form': form})