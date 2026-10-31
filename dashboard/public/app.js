/**
 * WORKPLACE MAKE FIRM — AI VIDEO PIPELINE MONITOR
 * Frontend Application Controller (Vanilla JS ES6)
 */

class DashboardApp {
  constructor() {
    this.jobs = [];
    this.selectedJobId = null;
    this.currentJob = null;
    this.overviewData = null;
    this.refreshIntervalMs = 5000;
    this.refreshTimer = null;
    this.currentLogPath = null;
    this.keyframeFilter = 'all';
    this.isAutoScroll = true;

    this.initElements();
    this.initEvents();
    this.start();
  }

  initElements() {
    // Navigation & controls
    this.serverClock = document.getElementById('serverClock');
    this.refreshSelect = document.getElementById('refreshSelect');
    this.btnManualRefresh = document.getElementById('btnManualRefresh');
    this.btnRunDiagnostics = document.getElementById('btnRunDiagnostics');
    this.btnOpenOrchestration = document.getElementById('btnOpenOrchestration');
    this.jobSearchInput = document.getElementById('jobSearchInput');
    this.heroTeamPills = document.getElementById('heroTeamPills');

    // Orchestration Modal
    this.orchestrationModal = document.getElementById('orchestrationModal');
    this.orchBackdrop = document.getElementById('orchBackdrop');
    this.orchClose = document.getElementById('orchClose');
    this.btnCloseOrch = document.getElementById('btnCloseOrch');
    this.orchScopeSelect = document.getElementById('orchScopeSelect');
    this.orchScopeHint = document.getElementById('orchScopeHint');
    this.orchMatrixContainer = document.getElementById('orchMatrixContainer');
    this.orchRosterGrid = document.getElementById('orchRosterGrid');
    this.orchestrationData = null;

    // KPI values
    this.valActiveJobs = document.getElementById('valActiveJobs');
    this.valCompletedJobs = document.getElementById('valCompletedJobs');
    this.valSourcesCount = document.getElementById('valSourcesCount');
    this.subSourcesDuration = document.getElementById('subSourcesDuration');
    this.jobsCountBadge = document.getElementById('jobsCountBadge');

    // Pipeline Stepper
    this.globalPipelineStepper = document.getElementById('globalPipelineStepper');

    // Sidebar
    this.jobsListContainer = document.getElementById('jobsListContainer');

    // Job Hero
    this.heroStatusBadge = document.getElementById('heroStatusBadge');
    this.heroJobId = document.getElementById('heroJobId');
    this.heroUpdateTime = document.getElementById('heroUpdateTime');
    this.heroTitle = document.getElementById('heroTitle');
    this.heroSourcePath = document.getElementById('heroSourcePath');
    this.heroRingProgress = document.getElementById('heroRingProgress');
    this.heroProgressPct = document.getElementById('heroProgressPct');
    this.heroNextActionText = document.getElementById('heroNextActionText');
    this.heroBlockerTag = document.getElementById('heroBlockerTag');
    this.heroBlockerText = document.getElementById('heroBlockerText');

    // Tabs
    this.workspaceTabs = document.getElementById('workspaceTabs');
    this.tabButtons = document.querySelectorAll('.tab-btn');
    this.tabPanels = document.querySelectorAll('.tab-panel');

    // Tab 1: Flow
    this.stagesTimelineList = document.getElementById('stagesTimelineList');

    // Tab 2: Budget
    this.scaleMin = document.getElementById('scaleMin');
    this.scaleTarget = document.getElementById('scaleTarget');
    this.scaleMax = document.getElementById('scaleMax');
    this.scaleSource = document.getElementById('scaleSource');
    this.budgetSafeZone = document.getElementById('budgetSafeZone');
    this.budgetActualMarker = document.getElementById('budgetActualMarker');
    this.budgetActualTag = document.getElementById('budgetActualTag');
    this.bSourceDur = document.getElementById('bSourceDur');
    this.bMinDur = document.getElementById('bMinDur');
    this.bTargetDur = document.getElementById('bTargetDur');
    this.bMaxDur = document.getElementById('bMaxDur');
    this.valAssessmentDur = document.getElementById('valAssessmentDur');
    this.lblAssessmentStatus = document.getElementById('lblAssessmentStatus');

    // Tab 3: Script
    this.scriptTitle = document.getElementById('scriptTitle');
    this.scriptSubtitle = document.getElementById('scriptSubtitle');
    this.emotionTagsBar = document.getElementById('emotionTagsBar');
    this.segmentsTableBody = document.getElementById('segmentsTableBody');
    this.scriptSearchInput = document.getElementById('scriptSearchInput');
    this.emotionFilter = document.getElementById('emotionFilter');

    // Tab 4: Keyframes & Timeline
    this.keyframesGrid = document.getElementById('keyframesGrid');
    this.keyframesSubtitle = document.getElementById('keyframesSubtitle');
    this.keyframeFilterBtns = document.getElementById('keyframeFilterBtns');
    this.timelineMdContent = document.getElementById('timelineMdContent');
    this.timelineMdText = document.getElementById('timelineMdText');
    this.btnToggleTimelineMd = document.getElementById('btnToggleTimelineMd');

    // Tab 5: Render
    this.clipsMatrixGrid = document.getElementById('clipsMatrixGrid');
    this.renderSummaryBadge = document.getElementById('renderSummaryBadge');
    this.finalVideoContainer = document.getElementById('finalVideoContainer');
    this.finalVideoPlayer = document.getElementById('finalVideoPlayer');
    this.finalVideoCard = document.getElementById('finalVideoCard');

    // Tab 6: Logs
    this.logFileSelect = document.getElementById('logFileSelect');
    this.terminalLines = document.getElementById('terminalLines');
    this.terminalWindow = document.getElementById('terminalWindow');
    this.chkAutoScroll = document.getElementById('chkAutoScroll');
    this.btnCopyLog = document.getElementById('btnCopyLog');

    // Modals
    this.imageLightbox = document.getElementById('imageLightbox');
    this.lightboxImg = document.getElementById('lightboxImg');
    this.lightboxCaption = document.getElementById('lightboxCaption');
    this.lightboxClose = document.getElementById('lightboxClose');
    this.lightboxBackdrop = document.getElementById('lightboxBackdrop');

    this.diagnosticsModal = document.getElementById('diagnosticsModal');
    this.diagLoading = document.getElementById('diagLoading');
    this.diagTerminal = document.getElementById('diagTerminal');
    this.diagOutput = document.getElementById('diagOutput');
    this.diagClose = document.getElementById('diagClose');
    this.diagBackdrop = document.getElementById('diagBackdrop');
    this.btnCloseDiag = document.getElementById('btnCloseDiag');
    this.btnRerunDiag = document.getElementById('btnRerunDiag');
  }

  initEvents() {
    // Refresh events
    this.refreshSelect.addEventListener('change', (e) => {
      this.refreshIntervalMs = parseInt(e.target.value, 10);
      this.resetAutoRefresh();
    });

    this.btnManualRefresh.addEventListener('click', () => {
      this.refreshAll();
    });

    // Tab switching
    this.tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.getAttribute('data-tab');
        this.switchTab(tabId);
      });
    });

    // Job search
    this.jobSearchInput.addEventListener('input', () => {
      this.renderJobsList();
    });

    // Script filter events
    this.scriptSearchInput.addEventListener('input', () => this.filterSegments());
    this.emotionFilter.addEventListener('change', () => this.filterSegments());

    // Keyframe category filters
    this.keyframeFilterBtns.querySelectorAll('.btn-chip').forEach(btn => {
      btn.addEventListener('click', () => {
        this.keyframeFilterBtns.querySelectorAll('.btn-chip').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.keyframeFilter = btn.getAttribute('data-cat');
        this.renderKeyframes();
      });
    });

    // Timeline toggle
    this.btnToggleTimelineMd.addEventListener('click', () => {
      const isExpanded = this.timelineMdContent.style.maxHeight === 'none';
      if (isExpanded) {
        this.timelineMdContent.style.maxHeight = '350px';
        this.btnToggleTimelineMd.innerText = 'Mở rộng toàn bộ';
      } else {
        this.timelineMdContent.style.maxHeight = 'none';
        this.btnToggleTimelineMd.innerText = 'Thu gọn';
      }
    });

    // Log select
    this.logFileSelect.addEventListener('change', (e) => {
      this.currentLogPath = e.target.value;
      this.fetchLogContent(this.currentLogPath);
    });

    this.chkAutoScroll.addEventListener('change', (e) => {
      this.isAutoScroll = e.target.checked;
    });

    this.btnCopyLog.addEventListener('click', () => {
      const text = this.terminalLines.innerText;
      navigator.clipboard.writeText(text).then(() => {
        const orig = this.btnCopyLog.innerText;
        this.btnCopyLog.innerText = '✓ Đã chép!';
        setTimeout(() => { this.btnCopyLog.innerText = orig; }, 1800);
      });
    });

    // Lightbox modal
    this.lightboxClose.addEventListener('click', () => this.closeLightbox());
    this.lightboxBackdrop.addEventListener('click', () => this.closeLightbox());

    // Diagnostics modal
    this.btnRunDiagnostics.addEventListener('click', () => this.runDiagnostics());
    this.diagClose.addEventListener('click', () => this.closeDiagnostics());
    this.diagBackdrop.addEventListener('click', () => this.closeDiagnostics());
    this.btnCloseDiag.addEventListener('click', () => this.closeDiagnostics());
    this.btnRerunDiag.addEventListener('click', () => this.runDiagnostics());

    // Orchestration modal
    this.btnOpenOrchestration.addEventListener('click', () => this.openOrchestrationModal());
    this.orchClose.addEventListener('click', () => this.closeOrchestrationModal());
    this.orchBackdrop.addEventListener('click', () => this.closeOrchestrationModal());
    this.btnCloseOrch.addEventListener('click', () => this.closeOrchestrationModal());
    this.orchScopeSelect.addEventListener('change', () => this.renderOrchestrationMatrix());

    // Keyboard escape
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.closeLightbox();
        this.closeDiagnostics();
        this.closeOrchestrationModal();
      }
    });

    // Live clock update
    setInterval(() => {
      const now = new Date();
      this.serverClock.innerText = now.toTimeString().split(' ')[0];
    }, 1000);
  }

  start() {
    this.refreshAll();
    this.resetAutoRefresh();
  }

  resetAutoRefresh() {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
    if (this.refreshIntervalMs > 0) {
      this.refreshTimer = setInterval(() => {
        this.refreshAll();
      }, this.refreshIntervalMs);
    }
  }

  async refreshAll() {
    try {
      await Promise.all([
        this.fetchOverview(),
        this.fetchJobs()
      ]);
    } catch (err) {
      console.error('Error refreshing monitor:', err);
    }
  }

  async fetchOverview() {
    const res = await fetch('/api/overview');
    if (!res.ok) return;
    const data = await res.json();
    this.overviewData = data;

    this.valActiveJobs.innerText = data.active_jobs;
    this.valCompletedJobs.innerText = data.completed_jobs;
    this.valSourcesCount.innerText = data.total_source_videos;
    this.subSourcesDuration.innerText = `Thời lượng: ${data.total_source_duration}`;
  }

  async fetchJobs() {
    const res = await fetch('/api/jobs');
    if (!res.ok) return;
    const data = await res.json();
    this.jobs = data.jobs || [];

    this.jobsCountBadge.innerText = this.jobs.length;

    // Pick selected job if none selected
    if (!this.selectedJobId && this.jobs.length > 0) {
      // Default to vision_ep02 or first active
      const inProg = this.jobs.find(j => j.job === 'vision_ep02') || this.jobs.find(j => j.status === 'RENDERING') || this.jobs[0];
      this.selectedJobId = inProg.job;
    }

    this.renderJobsList();

    if (this.selectedJobId) {
      await this.loadJobDetail(this.selectedJobId);
    }
  }

  async loadJobDetail(jobId) {
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) return;
    const job = await res.json();
    this.currentJob = job;

    this.renderJobHero(job);
    this.renderGlobalPipeline(job);
    this.renderTabFlow(job);
    this.renderTabBudget(job);
    this.renderTabScript(job);
    this.renderTabTimeline(job);
    this.renderTabRender(job);
    this.renderTabLogs(job);
  }

  selectJob(jobId) {
    this.selectedJobId = jobId;
    this.renderJobsList();
    this.loadJobDetail(jobId);
  }

  switchTab(tabId) {
    this.tabButtons.forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });
    this.tabPanels.forEach(p => {
      p.classList.toggle('active', p.id === tabId);
    });
  }

  /* -----------------------------------------------------------
     Renderers
  ------------------------------------------------------------ */

  renderJobsList() {
    const query = (this.jobSearchInput.value || '').toLowerCase().trim();
    const filtered = this.jobs.filter(j => {
      return j.job.toLowerCase().includes(query) || (j.title && j.title.toLowerCase().includes(query));
    });

    this.jobsListContainer.innerHTML = '';
    filtered.forEach(j => {
      const card = document.createElement('div');
      card.className = `job-card-item ${j.job === this.selectedJobId ? 'active' : ''}`;
      card.addEventListener('click', () => this.selectJob(j.job));

      let pillClass = 'pill-idle';
      if (j.status === 'RENDERING') pillClass = 'pill-rendering';
      else if (j.status === 'COMPLETED') pillClass = 'pill-completed';
      else if (j.status === 'READY') pillClass = 'pill-ready';

      card.innerHTML = `
        <div class="job-card-header">
          <span class="job-pill ${pillClass}">${j.status}</span>
          <span class="job-card-id">${j.job}</span>
        </div>
        <div class="job-card-title">${j.title || j.job}</div>
        <div class="job-card-meta">
          <span>Tiến độ: <strong>${j.overall_progress}%</strong></span>
          <span>${j.keyframes_count ? j.keyframes_count + ' frames' : ''}</span>
        </div>
        <div class="job-card-progress-bar">
          <div class="progress-fill" style="width: ${j.overall_progress}%"></div>
        </div>
      `;
      this.jobsListContainer.appendChild(card);
    });
  }

  renderGlobalPipeline(job) {
    const stages = job.stage_statuses || [];
    this.globalPipelineStepper.innerHTML = '';

    stages.forEach(st => {
      const stepEl = document.createElement('div');
      let statusClass = 'is-pending';
      let stateBadgeClass = 'state-pending';
      let stateText = 'Chờ';

      if (st.status === 'complete') {
        statusClass = 'is-complete';
        stateBadgeClass = 'state-complete';
        stateText = 'Xong';
      } else if (st.status === 'in_progress') {
        statusClass = 'is-inprogress';
        stateBadgeClass = 'state-inprogress';
        stateText = 'Chạy';
      }

      const ag = st.assigned_agent;
      const agentTagHtml = ag ? `<div class="stepper-agent-tag" style="border-left: 2px solid ${ag.color};"><span class="pill-icon">${ag.icon}</span> <span>${ag.name.split(' ')[0]}</span></div>` : '';

      stepEl.className = `stepper-step ${statusClass}`;
      stepEl.innerHTML = `
        <div class="step-top">
          <span class="step-num">STAGE 0${st.id}</span>
          <span class="step-state-badge ${stateBadgeClass}">${stateText}</span>
        </div>
        <div class="step-name">${st.name}</div>
        <div class="step-desc">${st.desc}</div>
        ${agentTagHtml}
      `;

      // Jump to tab on click
      stepEl.addEventListener('click', () => {
        if (st.id === 1 || st.id === 2) this.switchTab('tabTimeline');
        else if (st.id === 3) this.switchTab('tabScript');
        else if (st.id === 4) this.switchTab('tabBudget');
        else if (st.id === 5 || st.id === 6) this.switchTab('tabRender');
        else if (st.id === 7) this.switchTab('tabFlow');
      });

      this.globalPipelineStepper.appendChild(stepEl);
    });
  }

  renderJobHero(job) {
    this.heroTitle.innerText = job.title || job.job;
    this.heroJobId.innerText = `ID: ${job.job}`;
    this.heroSourcePath.innerText = job.source_video || 'Chưa liên kết video nguồn';

    let pillClass = 'pill-idle';
    if (job.status === 'RENDERING') pillClass = 'pill-rendering';
    else if (job.status === 'COMPLETED') pillClass = 'pill-completed';
    else if (job.status === 'READY') pillClass = 'pill-ready';

    this.heroStatusBadge.className = `hero-badge ${pillClass}`;
    this.heroStatusBadge.innerText = job.status;

    // Progress ring calculation (circumference: 2 * PI * 42 ≈ 263.89)
    const pct = Math.min(100, Math.max(0, job.overall_progress || 0));
    this.heroProgressPct.innerText = `${pct}%`;
    const offset = 264 - (264 * pct) / 100;
    this.heroRingProgress.style.strokeDashoffset = offset;

    // Render active agent team pills
    this.heroTeamPills.innerHTML = '';
    const seenAgents = new Set();
    (job.stage_statuses || []).forEach(st => {
      const ag = st.assigned_agent;
      if (ag && !seenAgents.has(ag.id)) {
        seenAgents.add(ag.id);
        const pill = document.createElement('div');
        pill.className = 'agent-team-pill';
        pill.title = `${ag.name} (${ag.role}) - Nhấp để điều phối`;
        pill.innerHTML = `<span class="pill-icon">${ag.icon}</span> <span>${ag.name}</span>`;
        pill.addEventListener('click', () => this.openOrchestrationModal(st.id));
        this.heroTeamPills.appendChild(pill);
      }
    });

    // Next Action banner
    this.heroNextActionText.innerText = job.next_action || 'Hệ thống đang chờ lệnh tiếp theo';
    if (job.blocker) {
      this.heroBlockerTag.style.display = 'block';
      this.heroBlockerText.innerText = job.blocker;
    } else {
      this.heroBlockerTag.style.display = 'none';
    }

    this.heroUpdateTime.innerText = `Cập nhật: ${new Date().toLocaleTimeString()}`;
  }

  renderTabFlow(job) {
    const stages = job.stage_statuses || [];
    this.stagesTimelineList.innerHTML = '';

    stages.forEach(st => {
      const card = document.createElement('div');
      let statusClass = 'is-pending';
      let badgeClass = 'state-pending';
      let badgeText = 'Đang chờ';

      if (st.status === 'complete') {
        statusClass = 'is-complete';
        badgeClass = 'state-complete';
        badgeText = 'Hoàn thành';
      } else if (st.status === 'in_progress') {
        statusClass = 'is-inprogress';
        badgeClass = 'state-inprogress';
        badgeText = 'Đang thực thi';
      }

      const ag = st.assigned_agent;
      const agentBoxHtml = ag ? `
        <div class="stage-agent-box">
          <div class="stage-agent-left">
            <div class="agent-avatar" style="border-color:${ag.color}; color:${ag.color};">${ag.icon}</div>
            <div class="agent-meta-info">
              <div class="agent-name-row">
                <span class="agent-name-text">${ag.name}</span>
                <span class="mode-badge mode-${ag.mode}">${this.getModeLabel(ag.mode)}</span>
              </div>
              <span class="agent-engine-text">${ag.engine}</span>
            </div>
          </div>
          <button class="btn-reassign-agent" data-stage="${st.id}">
            <span>⇄ Điều Phối Agent</span>
          </button>
        </div>
      ` : '';

      card.className = `stage-card-detail ${statusClass}`;
      card.innerHTML = `
        <div class="stage-icon-circle">0${st.id}</div>
        <div class="stage-body">
          <div class="stage-head-row">
            <div class="stage-main-title">${st.name} — ${st.desc}</div>
            <span class="stage-badge-tag ${badgeClass}">${badgeText}</span>
          </div>
          <div class="stage-text-desc">${st.detail || 'Giai đoạn trong dây chuyền sản xuất video review tự động.'}</div>
          ${agentBoxHtml}
          ${st.detail ? `<div class="stage-detail-note mt-2">✓ Kiểm chứng: ${st.detail}</div>` : ''}
        </div>
      `;

      // Reassign button event
      const reassignBtn = card.querySelector('.btn-reassign-agent');
      if (reassignBtn) {
        reassignBtn.addEventListener('click', () => {
          this.openOrchestrationModal(st.id);
        });
      }

      this.stagesTimelineList.appendChild(card);
    });
  }

  renderTabBudget(job) {
    const b = job.budget || {};
    const meta = job.source_metadata || {};
    const srcDur = b.source_duration || meta.duration || 0;

    const minDur = b.total_min || srcDur * 0.40;
    const maxDur = b.total_max || srcDur * 0.50;
    const targetDur = b.total_target || srcDur * 0.45;

    this.bSourceDur.innerText = this.formatTime(srcDur);
    this.bMinDur.innerText = `${this.formatTime(minDur)} (40%)`;
    this.bTargetDur.innerText = `${this.formatTime(targetDur)} (45%)`;
    this.bMaxDur.innerText = `${this.formatTime(maxDur)} (50%)`;

    this.scaleMin.innerText = `Min (40%): ${this.formatTime(minDur)}`;
    this.scaleTarget.innerText = `Target (45%): ${this.formatTime(targetDur)}`;
    this.scaleMax.innerText = `Max (50%): ${this.formatTime(maxDur)}`;
    this.scaleSource.innerText = `Gốc: ${this.formatTime(srcDur)}`;

    // Calculate marker for current render duration
    let actualDur = targetDur;
    const finalVid = job.render_clips && job.render_clips.final_video;
    if (finalVid) {
      actualDur = targetDur; // default target if completed
    }

    if (srcDur > 0) {
      const minPct = (minDur / srcDur) * 100;
      const maxPct = (maxDur / srcDur) * 100;
      const targetPct = (targetDur / srcDur) * 100;

      this.budgetSafeZone.style.left = `${minPct}%`;
      this.budgetSafeZone.style.width = `${maxPct - minPct}%`;
      this.budgetActualMarker.style.left = `${targetPct}%`;
      this.budgetActualTag.innerText = `Mục tiêu 45% (${this.formatTime(targetDur)})`;
    }

    // Assessment 10-20s section
    const assessTarget = b.assessment_target || 15.0;
    this.valAssessmentDur.innerText = `${assessTarget.toFixed(1)}s`;
    this.lblAssessmentStatus.innerText = '✓ ĐẠT CHUẨN 10–20S';
  }

  renderTabScript(job) {
    const script = job.script;
    if (!script || script.error) {
      this.scriptTitle.innerText = 'KỊCH BẢN CHƯA SẴN SÀNG';
      this.scriptSubtitle.innerText = 'Kịch bản review.json chưa được tạo hoặc đang chờ WRITE';
      this.segmentsTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 30px; color: var(--text-dim);">Chưa có kịch bản JSON cho job này.</td></tr>`;
      this.emotionTagsBar.innerHTML = '';
      return;
    }

    this.scriptTitle.innerText = `${script.title || 'KỊCH BẢN BIÊN TẬP'} (${script.total_segments} PHÂN ĐOẠN)`;
    this.scriptSubtitle.innerText = `File: ${job.script_filename} | Tổng số ${script.total_speech_units} speech units, ~${script.total_words} từ`;

    // Emotion Pills
    const emotions = script.emotions_distribution || {};
    this.emotionTagsBar.innerHTML = '';
    this.emotionFilter.innerHTML = '<option value="all">Tất cả cảm xúc</option>';

    Object.entries(emotions).forEach(([emo, count]) => {
      const pill = document.createElement('div');
      pill.className = 'emotion-pill';
      pill.innerHTML = `<span>${emo}</span> <span class="count">${count}</span>`;
      this.emotionTagsBar.appendChild(pill);

      const opt = document.createElement('option');
      opt.value = emo;
      opt.innerText = `${emo} (${count})`;
      this.emotionFilter.appendChild(opt);
    });

    this.filterSegments();
  }

  filterSegments() {
    if (!this.currentJob || !this.currentJob.script || !this.currentJob.script.segments) return;

    const query = (this.scriptSearchInput.value || '').toLowerCase().trim();
    const emoSelect = this.emotionFilter.value;
    const segments = this.currentJob.script.segments;

    const filtered = segments.filter(seg => {
      const matchText = (seg.first_text || '').toLowerCase().includes(query) ||
                        (seg.units && seg.units.some(u => u.text.toLowerCase().includes(query)));
      const matchEmo = emoSelect === 'all' || (seg.units && seg.units.some(u => u.emotion === emoSelect));
      return matchText && matchEmo;
    });

    this.segmentsTableBody.innerHTML = '';
    if (filtered.length === 0) {
      this.segmentsTableBody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 20px; color: var(--text-dim);">Không tìm thấy câu thoại phù hợp.</td></tr>`;
      return;
    }

    filtered.slice(0, 100).forEach(seg => {
      const tr = document.createElement('tr');
      const isAssessment = seg.section === 'assessment';
      const secBadge = isAssessment
        ? `<span class="section-badge sec-assessment">ĐÁNH GIÁ (15s)</span>`
        : `<span class="section-badge sec-story">CÂU CHUYỆN</span>`;

      const timeRange = (seg.source_start !== null && seg.source_end !== null)
        ? `<span class="source-time-pill">${this.formatTime(seg.source_start)} → ${this.formatTime(seg.source_end)}</span>`
        : `<span class="source-time-pill">--</span>`;

      let unitsHtml = '';
      (seg.units || []).forEach(u => {
        unitsHtml += `
          <div class="speech-unit-card">
            <span class="unit-emo-tag">[${u.emotion || 'normal'}]</span>
            <span>${this.escapeHtml(u.text)}</span>
          </div>
        `;
      });

      tr.innerHTML = `
        <td><span class="seg-id-badge">#${seg.id}</span></td>
        <td>${secBadge}</td>
        <td>${timeRange}</td>
        <td>${unitsHtml}</td>
        <td><span class="source-time-pill">${seg.shots_count || 1} shots</span></td>
      `;
      this.segmentsTableBody.appendChild(tr);
    });
  }

  renderTabTimeline(job) {
    this.keyframesSubtitle.innerText = `Tìm thấy ${job.keyframes_count || 0} hình ảnh trích xuất phục vụ kiểm chứng`;
    this.renderKeyframes();

    // Load timeline.md
    fetch(`/api/timeline-md?job=${job.job}`)
      .then(res => res.json())
      .then(data => {
        this.timelineMdText.innerText = data.content || 'Timeline chưa tạo.';
      })
      .catch(() => {
        this.timelineMdText.innerText = 'Không thể tải timeline.md';
      });
  }

  renderKeyframes() {
    if (!this.currentJob || !this.currentJob.keyframes) {
      this.keyframesGrid.innerHTML = '<div style="color:var(--text-dim); padding:20px;">Không có keyframe.</div>';
      return;
    }

    const filter = this.keyframeFilter;
    const frames = this.currentJob.keyframes.filter(f => {
      if (filter === 'all') return true;
      return f.category === filter;
    });

    this.keyframesGrid.innerHTML = '';
    if (frames.length === 0) {
      this.keyframesGrid.innerHTML = '<div style="color:var(--text-dim); padding:20px;">Không có keyframe trong mục này.</div>';
      return;
    }

    frames.forEach(f => {
      const card = document.createElement('div');
      card.className = 'keyframe-card';
      const mediaUrl = `/api/media?path=${encodeURIComponent(f.path)}`;

      card.innerHTML = `
        <div class="keyframe-img-wrap">
          <img src="${mediaUrl}" alt="${f.filename}" loading="lazy">
        </div>
        <div class="keyframe-caption" title="${f.filename}">${f.filename}</div>
      `;

      card.addEventListener('click', () => {
        this.openLightbox(mediaUrl, `${f.filename} (${f.size_human})`);
      });

      this.keyframesGrid.appendChild(card);
    });
  }

  renderTabRender(job) {
    const rc = job.render_clips || {};
    const totalClips = rc.total_clips || 0;
    const completedClips = rc.completed_clips || 0;

    this.renderSummaryBadge.innerText = `${completedClips}/${totalClips} Chunks Đã Render`;

    this.clipsMatrixGrid.innerHTML = '';
    const clips = rc.clips || [];

    if (clips.length === 0) {
      this.clipsMatrixGrid.innerHTML = '<div style="color:var(--text-dim); padding:20px;">Chưa có chunk render nào trong thư mục output.</div>';
    } else {
      clips.forEach(c => {
        const card = document.createElement('div');
        const isPending = c.is_pending;
        card.className = `clip-chunk-card ${isPending ? 'is-pending' : 'is-done'}`;
        card.innerHTML = `
          <div class="clip-name" title="${c.name}">${c.name}</div>
          <div class="clip-size">${c.size_human}</div>
          <div class="clip-status ${isPending ? 'status-pending' : 'status-done'}">
            ${isPending ? '⏳ ĐANG RENDER' : '✓ HOÀN THÀNH'}
          </div>
        `;
        this.clipsMatrixGrid.appendChild(card);
      });
    }

    // Final video preview
    const finalVid = rc.final_video;
    if (finalVid) {
      this.finalVideoCard.style.display = 'block';
      const videoUrl = `/api/media?path=${encodeURIComponent(finalVid.path)}`;
      if (this.finalVideoPlayer.src !== window.location.origin + videoUrl) {
        this.finalVideoPlayer.src = videoUrl;
      }
    } else {
      this.finalVideoCard.style.display = 'none';
      this.finalVideoPlayer.src = '';
    }
  }

  renderTabLogs(job) {
    const logs = job.logs || [];
    this.logFileSelect.innerHTML = '';

    if (logs.length === 0) {
      this.logFileSelect.innerHTML = '<option value="">Không có file log</option>';
      this.terminalLines.innerHTML = '<div style="color:var(--text-dim);">Chưa có file log trong data/handoff.</div>';
      return;
    }

    logs.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.path;
      opt.innerText = `${l.name} (${l.size_human})`;
      this.logFileSelect.appendChild(opt);
    });

    if (!this.currentLogPath || !logs.some(l => l.path === this.currentLogPath)) {
      this.currentLogPath = logs[0].path;
    }
    this.logFileSelect.value = this.currentLogPath;
    this.fetchLogContent(this.currentLogPath);
  }

  async fetchLogContent(path) {
    if (!path) return;
    try {
      const res = await fetch(`/api/logs?path=${encodeURIComponent(path)}`);
      if (!res.ok) return;
      const data = await res.json();
      this.renderTerminal(data.content || '');
    } catch (e) {
      this.terminalLines.innerHTML = `<div class="log-error">Lỗi đọc file log: ${e.message}</div>`;
    }
  }

  renderTerminal(content) {
    const lines = content.split('\n');
    this.terminalLines.innerHTML = '';

    lines.forEach((line, idx) => {
      const div = document.createElement('div');
      div.className = 'terminal-line';

      let lineClass = 'line-text';
      const upper = line.toUpperCase();
      if (upper.includes('ERROR') || upper.includes('FAIL')) lineClass += ' log-error';
      else if (upper.includes('WARN')) lineClass += ' log-warn';
      else if (upper.includes('PASS') || upper.includes('SUCCESS') || upper.includes('COMPLETE')) lineClass += ' log-pass';
      else if (upper.includes('INFO') || upper.includes('PROGRESS')) lineClass += ' log-info';

      div.innerHTML = `
        <span class="line-no">${idx + 1}</span>
        <span class="${lineClass}">${this.escapeHtml(line)}</span>
      `;
      this.terminalLines.appendChild(div);
    });

    if (this.isAutoScroll) {
      this.terminalWindow.scrollTop = this.terminalWindow.scrollHeight;
    }
  }

  async runDiagnostics() {
    this.diagnosticsModal.classList.add('active');
    this.diagLoading.style.display = 'block';
    this.diagTerminal.style.display = 'none';

    try {
      const res = await fetch('/api/check-environment', { method: 'POST' });
      const data = await res.json();
      this.diagLoading.style.display = 'none';
      this.diagTerminal.style.display = 'block';

      let out = data.stdout || '';
      if (data.stderr) out += '\n[STDERR]:\n' + data.stderr;
      this.diagOutput.innerText = out || 'Không có phản hồi từ check_environment.py';
    } catch (err) {
      this.diagLoading.style.display = 'none';
      this.diagTerminal.style.display = 'block';
      this.diagOutput.innerText = `Lỗi kiểm tra môi trường: ${err.message}`;
    }
  }

  closeDiagnostics() {
    this.diagnosticsModal.classList.remove('active');
  }

  openLightbox(src, caption) {
    this.lightboxImg.src = src;
    this.lightboxCaption.innerText = caption;
    this.imageLightbox.classList.add('active');
  }

  closeLightbox() {
    this.imageLightbox.classList.remove('active');
    this.lightboxImg.src = '';
  }

  /* -----------------------------------------------------------
     Agent Orchestration Methods
  ------------------------------------------------------------ */
  async openOrchestrationModal(focusStageId = null) {
    this.orchestrationModal.classList.add('active');
    await this.fetchOrchestration();
    this.populateOrchScopeSelect();
    this.renderOrchestrationMatrix(focusStageId);
    this.renderOrchestrationRoster();

    if (focusStageId) {
      setTimeout(() => {
        const targetRow = document.getElementById(`orchRowStage${focusStageId}`);
        if (targetRow) {
          targetRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
          targetRow.style.boxShadow = '0 0 20px var(--accent-cyan)';
          setTimeout(() => { targetRow.style.boxShadow = ''; }, 1800);
        }
      }, 200);
    }
  }

  closeOrchestrationModal() {
    this.orchestrationModal.classList.remove('active');
  }

  async fetchOrchestration() {
    try {
      const res = await fetch('/api/orchestration');
      if (!res.ok) return;
      this.orchestrationData = await res.json();
    } catch (err) {
      console.error('Error loading orchestration:', err);
    }
  }

  populateOrchScopeSelect() {
    const currentScope = this.orchScopeSelect.value;
    this.orchScopeSelect.innerHTML = `
      <option value="__default__">Cấu hình Mặc định Toàn Hệ Thống (Global Default)</option>
    `;

    (this.jobs || []).forEach(j => {
      const opt = document.createElement('option');
      opt.value = j.job;
      opt.innerText = `Dự án riêng: ${j.title || j.job} (${j.job})`;
      if (this.selectedJobId && j.job === this.selectedJobId && !currentScope) {
        opt.selected = true;
      }
      this.orchScopeSelect.appendChild(opt);
    });

    if (currentScope) {
      this.orchScopeSelect.value = currentScope;
    } else if (this.selectedJobId) {
      this.orchScopeSelect.value = this.selectedJobId;
    }
    this.updateOrchScopeHint();
  }

  updateOrchScopeHint() {
    const scope = this.orchScopeSelect.value;
    if (scope === '__default__') {
      this.orchScopeHint.innerText = 'Cấu hình chung sẽ áp dụng cho tất cả các job chưa có cấu hình ghi đè riêng.';
    } else {
      this.orchScopeHint.innerText = `Đang điều phối riêng cho dự án [${scope}].`;
    }
  }

  renderOrchestrationMatrix(focusStageId = null) {
    this.updateOrchScopeHint();
    if (!this.orchestrationData) return;

    const data = this.orchestrationData;
    const agents = data.agents || {};
    const candidates = data.stage_candidates || {};
    const cfg = data.config || {};
    const scope = this.orchScopeSelect.value;

    const stageNames = [
      { id: 1, name: "Source Intake & Video Discovery", desc: "Quét metadata & phân bổ ngân sách 40-50%" },
      { id: 2, name: "READ (Vision & Timeline Extraction)", desc: "Trích xuất timeline.md, đối chiếu clip & nhân vật" },
      { id: 3, name: "WRITE (Editorial Script & Narration)", desc: "Viết kịch bản review.json, SpeechUnits & assessment 15s" },
      { id: 4, name: "MEASURE & ZeroTTS Speech Synthesis", desc: "Tổng hợp giọng đọc Bảo Trang offline & đo PCM 48kHz" },
      { id: 5, name: "Shot Fitting & EDL Timeline", desc: "Khớp nhịp cắt video với speech units & xuất CapCut" },
      { id: 6, name: "FFmpeg Render & Video Assembly", desc: "Render song song chunk MKV & ghép final_review.mp4" },
      { id: 7, name: "QC & Compliance Certification", desc: "Kiểm tra bitstream H.264/AAC & chứng nhận thời lượng" },
    ];

    this.orchMatrixContainer.innerHTML = '';

    stageNames.forEach(st => {
      // Find current assignment
      let currentAssignment = null;
      if (scope !== '__default__' && cfg.job_overrides && cfg.job_overrides[scope] && cfg.job_overrides[scope][st.id]) {
        currentAssignment = cfg.job_overrides[scope][st.id];
      } else if (cfg.default_assignments && cfg.default_assignments[st.id]) {
        currentAssignment = cfg.default_assignments[st.id];
      }

      const assignedAgentId = currentAssignment ? currentAssignment.agent_id : (candidates[st.id] ? candidates[st.id][0] : 'hermes_orchestrator');
      const assignedMode = currentAssignment ? (currentAssignment.mode || 'autonomous') : 'autonomous';

      const row = document.createElement('div');
      row.className = 'orch-stage-row';
      row.id = `orchRowStage${st.id}`;

      // Candidates options
      const stageCands = candidates[st.id] || Object.keys(agents);
      let agentOptionsHtml = '';
      stageCands.forEach(cid => {
        const ag = agents[cid];
        if (ag) {
          const isSelected = cid === assignedAgentId ? 'selected' : '';
          agentOptionsHtml += `<option value="${ag.id}" ${isSelected}>${ag.icon} ${ag.name} (${ag.engine})</option>`;
        }
      });

      // Mode options
      const modeOptionsHtml = `
        <option value="autonomous" ${assignedMode === 'autonomous' ? 'selected' : ''}>⚡ Tự động (Autonomous)</option>
        <option value="ui_handoff" ${assignedMode === 'ui_handoff' ? 'selected' : ''}>🖥️ UI Handoff (Loopback)</option>
        <option value="manual_handoff" ${assignedMode === 'manual_handoff' ? 'selected' : ''}>✋ Thủ công (Manual Handoff)</option>
      `;

      row.innerHTML = `
        <div class="orch-stage-info">
          <div class="orch-stage-num">0${st.id}</div>
          <div>
            <div class="orch-stage-title">${st.name}</div>
            <div class="orch-stage-sub">${st.desc}</div>
          </div>
        </div>

        <div class="orch-agent-select-wrap">
          <select class="styled-select select-orch-agent" data-stage="${st.id}">
            ${agentOptionsHtml}
          </select>
        </div>

        <div class="orch-mode-select-wrap">
          <select class="styled-select select-orch-mode" data-stage="${st.id}">
            ${modeOptionsHtml}
          </select>
        </div>

        <div class="orch-action-wrap">
          <button class="btn-save-orch" data-stage="${st.id}">Lưu Gán</button>
        </div>
      `;

      // Save click handler
      const btnSave = row.querySelector('.btn-save-orch');
      const selectAgent = row.querySelector('.select-orch-agent');
      const selectMode = row.querySelector('.select-orch-mode');

      btnSave.addEventListener('click', async () => {
        const stageId = parseInt(btnSave.getAttribute('data-stage'), 10);
        const agentId = selectAgent.value;
        const mode = selectMode.value;
        const targetJob = scope === '__default__' ? null : scope;
        await this.saveStageAssignment(targetJob, stageId, agentId, mode, '', btnSave);
      });

      this.orchMatrixContainer.appendChild(row);
    });
  }

  async saveStageAssignment(job, stageId, agentId, mode, notes, btnEl) {
    const origText = btnEl.innerText;
    btnEl.innerText = 'Đang lưu...';
    btnEl.disabled = true;

    try {
      const res = await fetch('/api/orchestration', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job: job,
          stage_id: stageId,
          agent_id: agentId,
          mode: mode,
          notes: notes
        })
      });

      if (res.ok) {
        btnEl.innerText = '✓ Đã gán!';
        setTimeout(() => {
          btnEl.innerText = origText;
          btnEl.disabled = false;
        }, 1500);

        // Reload data
        await this.fetchOrchestration();
        if (this.selectedJobId) {
          await this.loadJobDetail(this.selectedJobId);
        }
      } else {
        btnEl.innerText = 'Lỗi!';
        setTimeout(() => {
          btnEl.innerText = origText;
          btnEl.disabled = false;
        }, 1800);
      }
    } catch (e) {
      btnEl.innerText = 'Lỗi mạng!';
      setTimeout(() => {
        btnEl.innerText = origText;
        btnEl.disabled = false;
      }, 1800);
    }
  }

  renderOrchestrationRoster() {
    if (!this.orchestrationData || !this.orchestrationData.agents) return;
    const agents = Object.values(this.orchestrationData.agents);
    this.orchRosterGrid.innerHTML = '';

    agents.forEach(ag => {
      const card = document.createElement('div');
      card.className = 'roster-card';
      card.style.borderLeft = `3px solid ${ag.color}`;

      card.innerHTML = `
        <div class="roster-top">
          <div class="roster-avatar-name">
            <span class="roster-icon">${ag.icon}</span>
            <div>
              <div class="roster-name">${ag.name}</div>
              <div class="roster-role">${ag.role}</div>
            </div>
          </div>
          <span class="mode-badge mode-${ag.default_mode}">${this.getModeLabel(ag.default_mode)}</span>
        </div>
        <div class="roster-desc">${ag.description}</div>
        <div class="roster-footer">
          <span>Engine: ${ag.engine}</span>
          <span>${ag.script_ref || ag.prompt_ref || 'Local Framework'}</span>
        </div>
      `;
      this.orchRosterGrid.appendChild(card);
    });
  }

  getModeLabel(mode) {
    if (mode === 'autonomous') return 'Tự động';
    if (mode === 'ui_handoff') return 'UI Handoff';
    if (mode === 'manual_handoff') return 'Thủ công';
    return mode || 'Auto';
  }

  /* -----------------------------------------------------------
     Utilities
  ------------------------------------------------------------ */
  formatTime(seconds) {
    if (seconds === null || seconds === undefined || isNaN(seconds)) return '--';
    const sec = Math.max(0, parseFloat(seconds));
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    const h = Math.floor(m / 60);
    const remM = m % 60;
    if (h > 0) {
      return `${h}:${remM.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${remM}:${s.toString().padStart(2, '0')}`;
  }

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

// Instantiate on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  window.app = new DashboardApp();
});
