from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from tastypie import http

from account.forms import SignUpForm


def signup(request):
    """ simple signup for users """
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


@csrf_exempt
def api_auth(request):
    """ authentication gate for the REST clients. Wraps the normal login method
    into JSON shell """
    if not request.method == "POST":
        return http.HttpMethodNotAllowed()

    form = AuthenticationForm(data=request.POST)
    if form.is_valid():
        login(request, form.get_user())
        return http.HttpAccepted()
    else:
        return http.HttpUnauthorized("Invalid credentials")