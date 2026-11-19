// 시연 페이지: demo-data.json(가상 입력 + 미리 돌린 AI 초안 + 대장 시점별 사본)과 src/rules.json(내 PC 도구와 같은 규칙)을 읽는다.
(async function () {
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const [rules, data] = await Promise.all([
    fetch("src/rules.json").then((r) => r.json()),
    fetch("site/demo-data.json").then((r) => r.json()),
  ]);
  const U = rules.unknown;
  $("#delayDays").textContent = rules.delay_days;

  // 방문자가 고른 사람 판정. 비어 있으면 시나리오 값을 쓴다.
  let overrides = {};
  try { overrides = JSON.parse(localStorage.getItem("ma-overrides") || "{}"); } catch (e) { overrides = {}; }
  const save = () => { try { localStorage.setItem("ma-overrides", JSON.stringify(overrides)); } catch (e) {} };

  const lastStage = data.stages[data.stages.length - 1];
  const scenarioIssue = (id) => lastStage.issues.find((r) => r["번호"] === id) || {};
  const effIssue = (row) => ({ ...row, ...(overrides[row["번호"]] || {}) });

  const riskTag = (g) => `<span class="risk ${g || "N"}">${g || "-"}</span>`;
  const val = (v) => (v === U ? `<span class="unk">미정</span>` : esc(v));

  // ── 1. 이슈 카드 ──
  function renderIssues() {
    const week = Number($("#weekSel").value);
    const list = data.messages.filter((m) => m.week === week);
    const sel = (id, field, opts) => {
      const cur = (overrides[id] && field in overrides[id]) ? overrides[id][field] : (scenarioIssue(id)[field] || "");
      return `<select data-id="${id}" data-f="${field}"><option value="">-</option>${opts.map((o) => `<option ${o === cur ? "selected" : ""}>${o}</option>`).join("")}</select>`;
    };
    let html = list.map((m) => {
      const d = m.draft, r = d.risk_suggestion;
      return `<article class="card">
        <div><h4>${esc(m.id)} · ${esc(m.received)} · ${esc(m.route)}</h4><div class="msg">${esc(m.masked)}</div></div>
        <div><h4>AI 초안<span class="ai">미리 돌린 결과</span></h4>
          <dl class="kv"><dt>재현 조건</dt><dd>${val(d.condition.value)}</dd><dt>증상</dt><dd>${val(d.symptom.value)}</dd><dt>기대 결과</dt><dd>${val(d.expected.value)}</dd>
          <dt>위험도 제안</dt><dd>${riskTag(r.grade)} <span class="q">근거 "${esc(r.quote)}"</span>${r.raised_from ? `<div class="raised">규칙: 안전 낱말 '${esc(r.safety_word)}' → ${esc(r.raised_from)}에서 A로 올림</div>` : ""}</dd></dl>
          ${(d.questions || []).length ? `<p class="q">현장에 되물을 질문: ${d.questions.map(esc).join(" / ")}</p>` : ""}
          ${(d.duplicate_of || []).length ? `<p class="dup">중복 의심: ${d.duplicate_of.join(", ")} (합치기는 사람이)</p>` : ""}
        </div>
        <div class="judge"><h4>사람 판정 · 대장 ${esc(m.ledger_id)}<span class="human">사람만</span></h4>
          <label>위험도 확정 ${sel(m.ledger_id, "위험도", ["A", "B", "C"])}</label>
          <label>판정 ${sel(m.ledger_id, "판정", rules.verdicts)}</label>
          <label>상태 ${sel(m.ledger_id, "상태", rules.issue_status)}</label>
        </div></article>`;
    }).join("");
    if (week === 2 && data.reply) {
      const r = data.reply;
      html += `<article class="card"><div><h4>되물은 답 · ${esc(r.target)}</h4><div class="msg">${esc(r.masked)}</div></div>
        <div><h4>AI 초안<span class="ai">미리 돌린 결과</span></h4><p class="q">'미정'이던 칸만 채움: ${Object.entries(r.filled).map(([k, v]) => `${esc(k)} → ${esc(v)}`).join(" · ") || "없음"}</p>
        <p class="q">이미 값이 있는 칸 · 사람 칸은 바꾸지 않습니다. 새 질문은 만들지 않습니다.</p></div><div></div></article>`;
    }
    $("#issueList").innerHTML = html;
    $("#issueList").querySelectorAll("select").forEach((s) => s.addEventListener("change", () => {
      overrides[s.dataset.id] = { ...(overrides[s.dataset.id] || {}), [s.dataset.f]: s.value };
      save(); renderCheck();
    }));
  }

  // ── 2. 회의 ──
  let curMeeting = 0;
  function renderMeetingTabs() {
    $("#meetingTabs").innerHTML = data.meetings.map((m, i) =>
      `<button role="tab" aria-selected="${i === curMeeting}" data-i="${i}">${i + 1}차 회의 · ${esc(m.date)}</button>`).join("");
    $("#meetingTabs").querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { curMeeting = Number(b.dataset.i); renderMeetingTabs(); renderMeeting(); }));
  }
  function renderMeeting() {
    const m = data.meetings[curMeeting], d = m.draft;
    const link = (t) => `<button class="t-link" data-t="${esc(t)}">${esc(t)}</button>`;
    const li = (arr, f) => (arr || []).map((x) => `<li>${esc(f(x))} ${(x.quotes || []).map(link).join(" ")}</li>`).join("") || "<li>없음</li>";
    $("#meetingView").innerHTML = `<div class="grid2">
      <div><h3>받아쓰기 텍스트 (입력)</h3><div class="transcript" id="tr">${m.lines.map((l) => `<div data-t="${esc(l.time)}"><b>${esc(l.time)}</b>${esc(l.text)}</div>`).join("")}</div></div>
      <div class="minutes"><h3>할 일 초안<span class="ai">미리 돌린 결과</span></h3>
        <div class="scroll"><table><tr><th>대장</th><th>할 일</th><th>담당</th><th>목표일</th><th>근거</th><th>이슈</th></tr>
        ${d.todos.map((t, i) => `<tr><td>${esc(m.added[i] || "")}</td><td>${esc(t.task)}</td><td>${val(t.owner)}</td><td>${val(t.due)}</td><td>${t.evidence_times.map(link).join(" ")}</td><td>${esc(t.related_issue || "")}</td></tr>`).join("") || `<tr><td colspan="6">할 일 없음</td></tr>`}
        </table></div>
        <h4>결정 사항</h4><ul>${li(d.decisions, (x) => x.text)}</ul>
        <h4>미결 사항</h4><ul>${li(d.open_items, (x) => x.text)}</ul>
        <p class="muted small">회의록 워드 맨 앞에는 이 회의 전 시점의 점검표가 들어갑니다. <a href="#check" data-stage="${esc(m.stage)}" id="toCheck">점검표 보기</a></p>
      </div></div>`;
    $("#meetingView").querySelectorAll(".t-link").forEach((b) => b.addEventListener("click", () => {
      const tr = $("#tr"); tr.querySelectorAll("div").forEach((x) => x.classList.toggle("hit", x.dataset.t === b.dataset.t));
      const hit = tr.querySelector(".hit"); if (hit) tr.scrollTop = hit.offsetTop - tr.offsetTop - 40;
    }));
    $("#toCheck").addEventListener("click", () => { $("#stageSel").value = m.stage; renderCheck(); });
  }

  // ── 3. 점검표 (rules.json 규칙) ──
  const toDate = (s) => (/^\d{4}-\d{2}-\d{2}$/.test(String(s)) ? new Date(s + "T00:00:00") : null);
  function build(stage) {
    const today = toDate(stage.date);
    const issues = stage.issues.map(effIssue);
    const issueRisk = Object.fromEntries(issues.map((r) => [r["번호"], r["위험도"]]));
    const items = [];
    stage.todos.forEach((t) => {
      if (t["상태"] === rules.todo_closed) return;
      const rel = t["관련 이슈 번호"];
      const risk = rel && overrides[rel] && "위험도" in overrides[rel] ? overrides[rel]["위험도"] : t["위험도"];
      items.push({ kind: "할 일", id: t["번호"], text: t["할 일"], owner: t["담당"], risk, status: t["상태"], due: t["목표일"] });
    });
    issues.forEach((r) => {
      if (r["상태"] === rules.issue_closed) return;
      items.push({ kind: "이슈", id: r["번호"], text: r["증상"], owner: "", risk: r["위험도"], status: r["상태"], due: r["목표일"], verdict: r["판정"] });
    });
    const order = rules.risk_order;
    items.forEach((it) => {
      const d = toDate(it.due);
      it.delayed = !!(d && (today - d) / 86400000 > rules.delay_days);
      it.r = order.includes(it.risk || "") ? order.indexOf(it.risk || "") : order.length;
      it.d = d ? d.getTime() : Infinity;
    });
    return items.sort((a, b) => a.r - b.r || a.d - b.d || a.id.localeCompare(b.id));
  }
  function renderCheck() {
    const stage = data.stages.find((s) => s.id === $("#stageSel").value) || data.stages[0];
    const items = build(stage);
    $("#checkCount").textContent = `기준일 ${stage.date} · 닫히지 않은 항목 ${items.length}건 · 지연 ${items.filter((x) => x.delayed).length}건`;
    $("#checkTable").innerHTML = `<tr><th>위험도</th><th>번호</th><th>구분</th><th>내용</th><th>담당</th><th>상태</th><th>판정</th><th>목표일</th><th>지연</th></tr>` +
      (items.map((it) => `<tr class="${it.delayed ? "delayed" : ""}"><td>${riskTag(it.risk)}</td><td>${esc(it.id)}</td><td>${it.kind}</td><td>${val(it.text)}</td><td>${val(it.owner)}</td><td>${esc(it.status)}</td><td>${esc(it.verdict || "")}</td><td>${val(it.due)}</td><td>${it.delayed ? '<span class="tag-delay">지연</span>' : ""}</td></tr>`).join("")
        || `<tr><td colspan="9">닫히지 않은 항목 없음</td></tr>`);
  }

  // ── 4. 검사 · 채점 ──
  $("#guardList").innerHTML = data.guard.map((g) => `<li>${esc(g)}</li>`).join("");
  $("#scoreTable").innerHTML = data.score.map((row, i) => `<tr>${row.map((c) => (i === 0 ? `<th>${esc(c)}</th>` : `<td>${esc(c)}</td>`)).join("")}</tr>`).join("");

  $("#stageSel").innerHTML = data.stages.map((s) => `<option value="${s.id}">${esc(s.label)}</option>`).join("");
  $("#weekSel").addEventListener("change", renderIssues);
  $("#stageSel").addEventListener("change", renderCheck);
  $("#fillHuman").addEventListener("click", () => { overrides = {}; save(); renderIssues(); renderCheck(); });
  $("#clearHuman").addEventListener("click", () => {
    overrides = {};
    data.messages.forEach((m) => { overrides[m.ledger_id] = { "위험도": "", "판정": "", "상태": rules.issue_status[0] }; });
    save(); renderIssues(); renderCheck();
  });
  renderIssues(); renderMeetingTabs(); renderMeeting(); renderCheck();
})();
