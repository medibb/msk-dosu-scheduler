"""공용 1계정(단일 비밀번호) 로그인.

치료사 소수가 공용으로 사용하므로 개인 계정·권한 분리 없이
세션 플래그(`authed`) 하나로 접근을 보호한다.
"""
import re

from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse


SESSION_KEY = 'authed'


def _exempt_patterns():
    return [re.compile(p) for p in getattr(settings, 'LOGIN_EXEMPT_URLS', [])]


class LoginRequiredMiddleware:
    """미인증 요청을 로그인 페이지로 보낸다(LOGIN_EXEMPT_URLS 제외)."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt = _exempt_patterns()

    def __call__(self, request):
        if not request.session.get(SESSION_KEY):
            path = request.path_info.lstrip('/')
            if not any(p.match(path) for p in self.exempt):
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        return self.get_response(request)


def login_view(request):
    error = None
    if request.method == 'POST':
        if request.POST.get('password') == settings.APP_PASSWORD:
            request.session[SESSION_KEY] = True
            return redirect(request.GET.get('next') or reverse('schedule'))
        error = '비밀번호가 올바르지 않습니다.'
    return render(request, 'login.html', {'error': error})


def logout_view(request):
    request.session.flush()
    return redirect(settings.LOGIN_URL)
