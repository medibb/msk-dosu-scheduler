// 주간 시간표 드래그앤드롭 (네이티브 HTML5 DnD, 외부 라이브러리 없음)
// 드롭 대상 3종: 시간표 칸(td.cell) / 예약 대기칸(td.resv-cell) / 대기자(#waitlist)
(function () {
  const layout = document.querySelector('.sched-layout');
  if (!layout) return;

  const URLS = {
    place: layout.dataset.placeUrl,
    unassign: layout.dataset.unassignUrl,
    reserve: layout.dataset.reserveUrl,
    unreserve: layout.dataset.unreserveUrl,
    addSession: layout.dataset.addSessionUrl,
  };

  function csrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }

  async function post(url, body) {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  let dragged = null;

  document.addEventListener('dragstart', function (e) {
    const card = e.target.closest('.card');
    if (!card) return;
    dragged = card;
    e.dataTransfer.effectAllowed = 'move';
  });

  function markOver(el, on) { el.classList.toggle('dragover', on); }

  function bindDropTargets() {
    document.querySelectorAll('td.cell, td.resv-cell, #waitlist').forEach(function (zone) {
      zone.addEventListener('dragover', function (e) { e.preventDefault(); markOver(zone, true); });
      zone.addEventListener('dragleave', function () { markOver(zone, false); });
      zone.addEventListener('drop', function (e) { e.preventDefault(); markOver(zone, false); onDrop(zone); });
    });
  }

  async function onDrop(zone) {
    if (!dragged) return;
    const card = dragged;
    dragged = null;

    // 1) 대기자로 복귀(배정 해제 / 예약 해제)
    if (zone.id === 'waitlist') {
      if (card.dataset.appointmentId) {
        const r = await post(URLS.unassign, { appointment_id: card.dataset.appointmentId });
        if (!r.ok) { alert('해제 실패'); return; }
        delete card.dataset.appointmentId;
        card.classList.remove('fixed');
      } else if (card.dataset.reserved) {
        const r = await post(URLS.unreserve, { patient_id: card.dataset.patientId });
        if (!r.ok) { alert('예약 해제 실패'); return; }
        delete card.dataset.reserved;
      }
      zone.appendChild(card);
      return;
    }

    // 2) 예약 대기칸에 넣기(여러 명 가능 → 점유 검사 없음)
    if (zone.dataset.reserve) {
      // 시간표에 배정돼 있던 카드면 먼저 배정 해제
      if (card.dataset.appointmentId) {
        const u = await post(URLS.unassign, { appointment_id: card.dataset.appointmentId });
        if (!u.ok) { alert('이동 실패'); return; }
        delete card.dataset.appointmentId;
      }
      const r = await post(URLS.reserve, {
        patient_id: card.dataset.patientId,
        weekday: zone.dataset.weekday,
        period: zone.dataset.period,
      });
      if (r.ok && r.data.ok) {
        card.dataset.reserved = '1';
        card.classList.remove('fixed');
        zone.appendChild(card);
      } else { alert(r.data.error || '예약 실패'); }
      return;
    }

    // 3) 시간표 칸에 배정(→ 시행중). 칸이 차 있으면 거부.
    if (zone.querySelector('.card')) { alert('이미 배정된 시간대입니다.'); return; }
    const r = await post(URLS.place, {
      patient_id: card.dataset.patientId,
      therapist_id: zone.dataset.therapist,
      weekday: zone.dataset.weekday,
      slot_index: zone.dataset.slot,
      appointment_id: card.dataset.appointmentId || null,
    });
    if (r.ok && r.data.ok) {
      card.dataset.appointmentId = r.data.card.appointment_id;
      delete card.dataset.reserved;
      zone.appendChild(card);
    } else {
      alert(r.data.error || '배정 실패');
    }
  }

  // 더블클릭: 도수치료 회차 +1 기록 (시간표에 배정된 카드만)
  document.addEventListener('dblclick', async function (e) {
    if (e.target.closest('a')) return;              // 이름 링크 더블클릭은 무시
    const card = e.target.closest('.card');
    if (!card || !card.dataset.appointmentId) return;
    const nameEl = card.querySelector('.nm a, .nm');
    const name = nameEl ? nameEl.textContent.trim() : '';
    if (!confirm(name + ' 회차 +1을 기록할까요?')) return;
    const r = await post(URLS.addSession, { patient_id: card.dataset.patientId });
    if (r.ok && r.data.ok) {
      const sess = card.querySelector('.sess');
      if (sess) sess.textContent = r.data.used + '/' + r.data.target;
      if (r.data.alert) alert(r.data.alert);
    } else {
      alert((r.data && r.data.error) || '회차 기록 실패');
    }
  });

  bindDropTargets();
})();
