// 주간 시간표 드래그앤드롭 (네이티브 HTML5 DnD, 외부 라이브러리 없음)
(function () {
  const layout = document.querySelector('.sched-layout');
  if (!layout) return;

  const therapistId = layout.dataset.therapistId;
  const URLS = {
    place: layout.dataset.placeUrl,
    unassign: layout.dataset.unassignUrl,
    fixed: layout.dataset.fixedUrl,
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

  // 드롭 타깃: 그리드 칸과 대기자 패널
  function bindDropTargets() {
    document.querySelectorAll('td.cell, #waitlist').forEach(function (zone) {
      zone.addEventListener('dragover', function (e) { e.preventDefault(); markOver(zone, true); });
      zone.addEventListener('dragleave', function () { markOver(zone, false); });
      zone.addEventListener('drop', function (e) { e.preventDefault(); markOver(zone, false); onDrop(zone); });
    });
  }

  async function onDrop(zone) {
    if (!dragged) return;
    const card = dragged;
    dragged = null;

    if (zone.id === 'waitlist') {
      // 그리드 → 대기자(배정 해제)
      const apptId = card.dataset.appointmentId;
      if (!apptId) { zone.appendChild(card); return; }  // 대기자끼리 이동
      const r = await post(URLS.unassign, { appointment_id: apptId });
      if (r.ok) {
        delete card.dataset.appointmentId;
        card.classList.remove('fixed');
        zone.appendChild(card);
      } else { alert('해제 실패'); }
      return;
    }

    // 칸이 이미 차 있으면 거부
    if (zone.querySelector('.card')) { alert('이미 배정된 시간대입니다.'); return; }

    const r = await post(URLS.place, {
      patient_id: card.dataset.patientId,
      therapist_id: therapistId,
      weekday: zone.dataset.weekday,
      slot_index: zone.dataset.slot,
      appointment_id: card.dataset.appointmentId || null,
    });
    if (r.ok && r.data.ok) {
      card.dataset.appointmentId = r.data.card.appointment_id;
      zone.appendChild(card);
    } else {
      alert(r.data.error || '배정 실패');
    }
  }

  // 더블클릭: 스케줄 고정 토글
  document.addEventListener('dblclick', async function (e) {
    const card = e.target.closest('.card');
    if (!card || !card.dataset.appointmentId) return;
    const r = await post(URLS.fixed, { appointment_id: card.dataset.appointmentId });
    if (r.ok) card.classList.toggle('fixed', r.data.is_fixed);
  });

  bindDropTargets();
})();
