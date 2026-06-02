from django.shortcuts import render

from .models import Settings


def schedule(request):
    """주간 시간표 그리드(상세 구현은 3.0). 현재는 골격."""
    settings_obj = Settings.load()
    return render(request, 'schedule.html', {
        'time_slots': settings_obj.time_slots,
    })


def waitlist(request):
    """대기자 패널(상세 구현은 2.0)."""
    return render(request, 'placeholder.html', {'title': '대기자'})


def stats(request):
    """통계(상세 구현은 5.0)."""
    return render(request, 'placeholder.html', {'title': '통계'})


def import_excel(request):
    """엑셀 임포트(상세 구현은 2.0)."""
    return render(request, 'placeholder.html', {'title': '엑셀 임포트'})
