const API = "";

async function api(method, path, body = null) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  return res.json();
}

function renderMd(md) {
  if (!md) return "";
  if (typeof marked !== "undefined") return marked.parse(md);
  return md
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>")
    .replace(/^- (.+)$/gm, "<li>$1</li>")
    .replace(/^(\d+)\.\s+(.+)$/gm, "<li><strong>$1.</strong> $2</li>")
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

function appData() {
  return {
    page: "dashboard",
    loading: {},
    dashLoading: true,
    toast: { show: false, msg: "", type: "success" },

    fetchWeeks: 12,
    maxReviews: 3000,

    stats: {
      reviews: 0, themes: 0, classifications: 0,
      avgRating: 0, latestNote: null, lastFetched: null,
      ratingDist: { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 },
      dateRange: null,
    },
    themes: [],
    classificationDist: {},
    latestPulse: null,
    pulseList: [],

    pipelineStep: 0,
    pipelineResults: {},
    pipelineRunning: false,
    pipelineLog: [],

    generatedReport: null,
    emlFile: null,

    emailRecipient: "",
    emailName: "",

    async init() {
      await this.loadDashboard();
    },

    notify(msg, type = "success") {
      this.toast = { show: true, msg, type };
      setTimeout(() => (this.toast.show = false), 5000);
    },

    setLoading(key, val) {
      this.loading = { ...this.loading, [key]: val };
    },
    isLoading(key) {
      return !!this.loading[key];
    },

    addLog(msg) {
      const now = new Date().toLocaleTimeString();
      this.pipelineLog.push({ time: now, msg });
    },

    async loadDashboard() {
      this.dashLoading = true;
      try {
        const [statsRes, themeRes, classRes, noteRes] = await Promise.allSettled([
          api("GET", "/api/reviews/stats"),
          api("GET", "/api/themes"),
          api("GET", "/api/themes/classifications"),
          api("GET", "/api/weekly-note/latest"),
        ]);

        if (statsRes.status === "fulfilled" && statsRes.value.success) {
          const d = statsRes.value.data;
          this.stats.reviews = d.total_count || 0;
          this.stats.avgRating = d.average_rating || 0;
          this.stats.lastFetched = d.last_fetched || null;
          this.stats.ratingDist = d.rating_distribution || this.stats.ratingDist;
          this.stats.dateRange = d.date_range || null;
        }
        if (themeRes.status === "fulfilled" && themeRes.value.success) {
          const d = themeRes.value.data;
          this.stats.themes = d.theme_count || 0;
          this.themes = d.themes || [];
        }
        if (classRes.status === "fulfilled" && classRes.value.success) {
          const d = classRes.value.data;
          this.stats.classifications = d.total_classified || 0;
          this.classificationDist = d.theme_distribution || {};
        }
        if (noteRes.status === "fulfilled" && noteRes.value.success && noteRes.value.data) {
          this.latestPulse = noteRes.value.data;
          this.stats.latestNote = noteRes.value.data.report_date;
        }
      } catch (e) {
        console.error("Dashboard load error:", e);
      }
      this.dashLoading = false;
    },

    themeReviewCount(themeId) {
      return this.classificationDist[themeId] || 0;
    },

    totalRatings() {
      return Object.values(this.stats.ratingDist).reduce((a, b) => a + b, 0);
    },
    ratingPct(star) {
      const total = this.totalRatings();
      if (!total) return 0;
      return Math.round(((this.stats.ratingDist[String(star)] || 0) / total) * 100);
    },

    async handleFetchReviews() {
      this.setLoading("fetch", true);
      this.addLog(`Fetching reviews (${this.fetchWeeks} weeks, max ${this.maxReviews})...`);
      try {
        const res = await api("POST", "/api/reviews/fetch", {
          weeks: this.fetchWeeks,
          max_reviews: this.maxReviews,
        });
        if (res.success) {
          this.pipelineResults.fetch = res.data;
          const msg = `Fetched ${res.data.total_count} reviews (${res.data.raw_fetched} raw, ${res.data.filtered_out} filtered)`;
          this.addLog(msg);
          this.notify(msg);
          this.pipelineStep = Math.max(this.pipelineStep, 1);
          await this.loadDashboard();
        } else {
          this.addLog("Fetch failed: " + (res.detail || "Unknown error"));
          this.notify(res.detail || "Fetch failed", "error");
        }
      } catch (e) {
        this.addLog("Fetch error: " + e.message);
        this.notify(e.message, "error");
      }
      this.setLoading("fetch", false);
    },

    async handleGenerateThemes() {
      this.setLoading("themes", true);
      this.addLog("Discovering themes with Groq LLM...");
      try {
        const res = await api("POST", "/api/themes/generate");
        if (res.success) {
          this.pipelineResults.themes = res.data;
          this.themes = res.data.themes || [];
          const msg = `Discovered ${res.data.theme_count} themes from ${res.data.review_count_used} reviews`;
          this.addLog(msg);
          this.notify(msg);
          this.pipelineStep = Math.max(this.pipelineStep, 2);
          await this.loadDashboard();
        } else {
          this.addLog("Theme generation failed");
          this.notify(res.detail || "Theme generation failed", "error");
        }
      } catch (e) {
        this.addLog("Theme error: " + e.message);
        this.notify(e.message, "error");
      }
      this.setLoading("themes", false);
    },

    async handleClassifyReviews() {
      this.setLoading("classify", true);
      this.addLog("Classifying reviews into themes (this takes several minutes)...");
      try {
        const res = await api("POST", "/api/themes/classify");
        if (res.success) {
          this.pipelineResults.classify = res.data;
          this.classificationDist = res.data.theme_distribution || {};
          const msg = `Classified ${res.data.total_classified} reviews`;
          this.addLog(msg);
          this.notify(msg);
          this.pipelineStep = Math.max(this.pipelineStep, 3);
          await this.loadDashboard();
        } else {
          this.addLog("Classification failed");
          this.notify(res.detail || "Classification failed", "error");
        }
      } catch (e) {
        this.addLog("Classify error: " + e.message);
        this.notify(e.message, "error");
      }
      this.setLoading("classify", false);
    },

    async handleGenerateNote() {
      this.setLoading("generate", true);
      this.addLog("Generating weekly pulse note with Gemini...");
      try {
        const res = await api("POST", `/api/weekly-note/generate?weeks=${this.fetchWeeks}`);
        if (res.success) {
          this.pipelineResults.note = res.data;
          this.latestPulse = res.data;
          this.generatedReport = res.data;
          const msg = `Pulse note generated for ${res.data.report_date}`;
          this.addLog(msg);
          this.notify(msg);
          this.pipelineStep = Math.max(this.pipelineStep, 4);
          await this.loadDashboard();
        } else {
          this.addLog("Note generation failed");
          this.notify(res.detail || "Note generation failed", "error");
        }
      } catch (e) {
        this.addLog("Generate error: " + e.message);
        this.notify(e.message, "error");
      }
      this.setLoading("generate", false);
    },

    async handleDraftEmail() {
      if (!this.emailRecipient) return this.notify("Enter a recipient email", "error");
      this.setLoading("email", true);
      this.addLog("Saving email draft (.eml)...");
      try {
        const res = await api("POST", "/api/email/draft", {
          recipient: this.emailRecipient,
          recipient_name: this.emailName || null,
        });
        if (res.success) {
          this.emlFile = res.data.report_date;
          this.addLog("Draft saved: " + res.data.eml_file);
          this.notify("Draft saved. Click Download to get the .eml file.");
        } else {
          this.notify(res.detail || "Draft failed", "error");
        }
      } catch (e) {
        this.notify(e.message, "error");
      }
      this.setLoading("email", false);
    },

    async handleSendEmail() {
      if (!this.emailRecipient) return this.notify("Enter a recipient email", "error");
      this.setLoading("email", true);
      this.addLog("Sending email to " + this.emailRecipient + "...");
      try {
        const res = await api("POST", "/api/email/send", {
          recipient: this.emailRecipient,
          recipient_name: this.emailName || null,
          send: true,
        });
        if (res.success) {
          this.emlFile = res.data.report_date;
          const msg = `Email sent to ${res.data.to}`;
          this.addLog(msg);
          this.notify(msg);
          this.pipelineStep = Math.max(this.pipelineStep, 5);
        } else {
          this.notify(res.detail || "Send failed", "error");
        }
      } catch (e) {
        this.addLog("Send error: " + e.message);
        this.notify(e.message, "error");
      }
      this.setLoading("email", false);
    },

    async downloadPdf() {
      if (!this.latestPulse || !this.latestPulse.markdown_content) {
        return this.notify("No pulse note available. Generate one first.", "error");
      }
      try {
        const res = await fetch("/api/weekly-note/download-pdf", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            markdown_content: this.latestPulse.plaintext_content || this.latestPulse.markdown_content,
            report_date: this.latestPulse.report_date || "",
          }),
        });
        if (!res.ok) throw new Error("PDF generation failed");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `pulse-${this.latestPulse.report_date || "report"}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
      } catch (e) {
        this.notify(e.message, "error");
      }
    },

    async handleRunAll() {
      this.pipelineRunning = true;
      this.pipelineStep = 0;
      this.pipelineResults = {};
      this.pipelineLog = [];
      this.generatedReport = null;
      this.emlFile = null;

      this.addLog("Starting full pipeline...");

      await this.handleFetchReviews();
      if (this.pipelineStep < 1) { this.pipelineRunning = false; return; }

      await this.handleGenerateThemes();
      if (this.pipelineStep < 2) { this.pipelineRunning = false; return; }

      await this.handleClassifyReviews();
      if (this.pipelineStep < 3) { this.pipelineRunning = false; return; }

      await this.handleGenerateNote();
      if (this.pipelineStep < 4) { this.pipelineRunning = false; return; }

      this.addLog("Pipeline complete. Weekly report is ready below.");
      this.pipelineRunning = false;
    },

    async loadPulseList() {
      try {
        const res = await api("GET", "/api/weekly-note/list");
        if (res.success) this.pulseList = res.data || [];
      } catch (e) {
        console.error(e);
      }
    },

    async loadPulseByDate(date) {
      try {
        const res = await api("GET", `/api/weekly-note/${date}`);
        if (res.success && res.data) this.latestPulse = res.data;
      } catch (e) {
        this.notify("Note not found", "error");
      }
    },

    navigateTo(pg) {
      this.page = pg;
      if (pg === "dashboard") this.loadDashboard();
      if (pg === "pulse") { this.loadDashboard(); this.loadPulseList(); }
    },

    formatDate(iso) {
      if (!iso) return "N/A";
      try {
        return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
      } catch { return iso; }
    },

    timeAgo(iso) {
      if (!iso) return "Never";
      try {
        const diff = Date.now() - new Date(iso).getTime();
        const mins = Math.floor(diff / 60000);
        if (mins < 1) return "Just now";
        if (mins < 60) return mins + "m ago";
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return hrs + "h ago";
        return Math.floor(hrs / 24) + "d ago";
      } catch { return iso; }
    },
  };
}
