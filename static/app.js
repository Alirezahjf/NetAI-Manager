(() => {
  const $ = (s) => document.querySelector(s);
  const state = {
    conversations: [],
    active: null,
    pendingPlatform: null,
    phoneCodeHash: null,
    transactionHash: null,
  };

  const PLAT_LABEL = {
    telegram: "TG", bale: "بله", rubika: "رو", rubino: "نو",
    soroush: "سر", email: "@", youtube: "YT",
  };

  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
      ...opts,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const j = await res.json();
        detail = j.detail || JSON.stringify(j);
      } catch {}
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return res.json();
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function platColor(meta) {
    return (meta && meta.color) || "#64748b";
  }

  // ---- Inbox ----
  function renderConversations(filter = "") {
    const list = $("#conv-list");
    list.innerHTML = "";
    const q = filter.trim();
    const items = state.conversations.filter((c) => {
      if (!q) return true;
      return (c.title || "").includes(q) || (c.platform || "").includes(q);
    });
    if (!items.length) {
      list.innerHTML = `<div class="muted" style="padding:1rem;text-align:center">گفتگویی نیست. از تنظیمات وصل کنید.</div>`;
      return;
    }
    for (const c of items) {
      const el = document.createElement("div");
      el.className = "conv-item" + (state.active && state.active.id === c.id ? " active" : "");
      const color = platColor(c.meta);
      el.innerHTML = `
        <div class="avatar" style="background:${color}">
          ${(c.title || "?").slice(0, 1)}
          <span class="plat-dot" style="background:${color}"></span>
        </div>
        <div class="meta">
          <strong>${escapeHtml(c.title || c.chat_id || "بدون عنوان")}</strong>
          <span>${escapeHtml(c.meta?.name || c.platform)} · ${escapeHtml(c.last_message || "—")}</span>
        </div>
        ${c.unread ? `<span class="unread">${c.unread}</span>` : ""}
      `;
      el.onclick = () => openConversation(c);
      list.appendChild(el);
    }
  }

  async function loadConversations() {
    try {
      const data = await api("/api/inbox/conversations");
      state.conversations = data.conversations || [];
      $("#account-count").textContent = `${state.conversations.length} گفتگو`;
      renderConversations($("#search").value);
    } catch (e) {
      $("#conv-list").innerHTML = `<div class="muted" style="padding:1rem">${escapeHtml(e.message)}</div>`;
    }
  }

  async function openConversation(c) {
    state.active = c;
    renderConversations($("#search").value);
    $("#chat-title").textContent = c.title || c.chat_id;
    $("#chat-sub").textContent = `${c.meta?.name || c.platform} · ${c.account_name || c.account_id}`;
    const badge = $("#chat-platform-badge");
    badge.hidden = false;
    badge.style.background = platColor(c.meta);
    badge.textContent = PLAT_LABEL[c.platform] || "?";
    $("#composer").hidden = false;
    $("#btn-ai-reply").disabled = false;

    const box = $("#messages");
    box.innerHTML = `<div class="muted" style="margin:auto">در حال بارگذاری…</div>`;
    try {
      const data = await api(
        `/api/inbox/messages?platform=${encodeURIComponent(c.platform)}&account_id=${encodeURIComponent(c.account_id)}&chat_id=${encodeURIComponent(c.chat_id)}`
      );
      box.innerHTML = "";
      const color = platColor(data.meta || c.meta);
      const label = PLAT_LABEL[c.platform] || "?";
      for (const m of data.messages || []) {
        const div = document.createElement("div");
        div.className = "msg " + (m.is_outgoing ? "out" : "in");
        div.innerHTML = `
          <div class="msg-meta">
            <span class="mini-plat" style="background:${color}">${label}</span>
            <span>${m.is_outgoing ? "شما" : escapeHtml(m.sender_name || m.sender_id || "")}</span>
          </div>
          <div>${escapeHtml(m.text || "")}</div>
          ${m.timestamp ? `<time>${escapeHtml(m.timestamp)}</time>` : ""}
        `;
        box.appendChild(div);
      }
      box.scrollTop = box.scrollHeight;
    } catch (e) {
      box.innerHTML = `<div class="muted" style="margin:auto">${escapeHtml(e.message)}</div>`;
    }
  }

  $("#composer").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (!state.active) return;
    const text = $("#composer-input").value.trim();
    if (!text) return;
    $("#btn-send").disabled = true;
    try {
      await api("/api/inbox/send", {
        method: "POST",
        body: JSON.stringify({
          platform: state.active.platform,
          account_id: state.active.account_id,
          chat_id: state.active.chat_id,
          text,
        }),
      });
      $("#composer-input").value = "";
      await openConversation(state.active);
    } catch (e) {
      alert(e.message);
    } finally {
      $("#btn-send").disabled = false;
    }
  });

  $("#btn-ai-reply").addEventListener("click", async () => {
    if (!state.active) return;
    const lastIn = [...document.querySelectorAll(".msg.in")].pop();
    const text = lastIn ? lastIn.innerText : "";
    if (!text) return alert("پیام ورودی برای پاسخ نیست");
    try {
      const data = await api("/api/ai/reply", {
        method: "POST",
        body: JSON.stringify({
          message_text: text,
          platform: state.active.platform,
          chat_context: state.active.title || "",
        }),
      });
      $("#composer-input").value = data.reply || "";
      $("#composer-input").focus();
    } catch (e) {
      alert(e.message);
    }
  });

  $("#btn-refresh").onclick = () => loadConversations();
  $("#search").oninput = (e) => renderConversations(e.target.value);

  // ---- Settings + Adam-style connect ----
  function openSettings() {
    $("#settings-overlay").hidden = false;
    $("#settings-panel").hidden = false;
    loadSettingsForm();
    loadPlatformCards();
  }
  function closeSettings() {
    $("#settings-overlay").hidden = true;
    $("#settings-panel").hidden = true;
  }
  $("#btn-settings").onclick = openSettings;
  $("#btn-close-settings").onclick = closeSettings;
  $("#settings-overlay").onclick = closeSettings;

  async function loadPlatformCards() {
    const box = $("#platform-cards");
    box.innerHTML = `<div class="muted">در حال بارگذاری…</div>`;
    try {
      const data = await api("/api/accounts/status");
      if (data.phone) $("#s-phone").value = data.phone;
      box.innerHTML = "";
      for (const p of data.platforms || []) {
        const card = document.createElement("div");
        card.className = "plat-card" + (p.connected ? " connected" : "");
        const short = PLAT_LABEL[p.platform] || p.name.slice(0, 2);
        card.innerHTML = `
          <div class="dot" style="background:${p.color}">${short}</div>
          <div class="info">
            <strong>${escapeHtml(p.name)}</strong>
            <span>${p.connected ? "متصل" : (p.needs_phone ? "نیاز به کد تأیید" : "نیاز به اعتبارنامه")}</span>
          </div>
          <span class="check">✓</span>
          <button type="button">${p.connected ? "قطع" : "اتصال"}</button>
        `;
        const btn = card.querySelector("button");
        btn.onclick = () => onPlatformAction(p);
        box.appendChild(card);
      }
    } catch (e) {
      box.innerHTML = `<div class="muted">${escapeHtml(e.message)}</div>`;
    }
  }

  async function onPlatformAction(p) {
    if (p.connected) {
      const acc = (p.accounts || [])[0];
      if (!acc) return;
      if (!confirm(`قطع اتصال ${p.name}؟`)) return;
      try {
        await api(`/api/accounts/${p.platform}/${encodeURIComponent(acc.account_id)}/disconnect`, {
          method: "POST",
        });
        await loadPlatformCards();
        await loadConversations();
      } catch (e) {
        alert(e.message);
      }
      return;
    }

    if (!p.needs_phone) {
      alert(`${p.name}: اتصال از طریق اعتبارنامه / API جداگانه است (فعلاً از Swagger).`);
      return;
    }

    const phone = $("#s-phone").value.trim();
    if (!phone) {
      alert("اول شماره موبایل را ذخیره کنید.");
      return;
    }

    try {
      // ensure phone saved
      await api("/api/accounts/phone", {
        method: "PUT",
        body: JSON.stringify({ phone }),
      });
      const res = await api("/api/accounts/send-code", {
        method: "POST",
        body: JSON.stringify({ platform: p.platform, phone }),
      });
      if (res.status === "already_connected" || res.status === "connected") {
        await loadPlatformCards();
        await loadConversations();
        return;
      }
      state.pendingPlatform = p.platform;
      state.phoneCodeHash = res.phone_code_hash || null;
      state.transactionHash = res.transaction_hash || null;
      $("#code-modal-title").textContent = `کد ${p.name}`;
      $("#code-modal-desc").textContent =
        res.message || "کد را از SMS یا داخل همان پیام‌رسان وارد کنید.";
      $("#code-input").value = "";
      $("#code-error").textContent = "";
      $("#code-modal").hidden = false;
      $("#code-input").focus();
    } catch (e) {
      alert(e.message);
    }
  }

  $("#btn-code-cancel").onclick = () => {
    $("#code-modal").hidden = true;
    state.pendingPlatform = null;
  };

  $("#btn-code-ok").onclick = async () => {
    const code = $("#code-input").value.trim();
    if (!code || !state.pendingPlatform) return;
    $("#btn-code-ok").disabled = true;
    $("#code-error").textContent = "";
    try {
      await api("/api/accounts/verify-code", {
        method: "POST",
        body: JSON.stringify({
          platform: state.pendingPlatform,
          code,
          phone: $("#s-phone").value.trim(),
          phone_code_hash: state.phoneCodeHash,
          transaction_hash: state.transactionHash,
        }),
      });
      $("#code-modal").hidden = true;
      state.pendingPlatform = null;
      await loadPlatformCards();
      await loadConversations();
    } catch (e) {
      $("#code-error").textContent = e.message;
    } finally {
      $("#btn-code-ok").disabled = false;
    }
  };

  $("#btn-save-phone").onclick = async () => {
    const phone = $("#s-phone").value.trim();
    if (!phone) return;
    try {
      await api("/api/accounts/phone", {
        method: "PUT",
        body: JSON.stringify({ phone }),
      });
      $("#phone-status").textContent = "شماره ذخیره شد ✓";
    } catch (e) {
      $("#phone-status").textContent = e.message;
    }
  };

  async function loadSettingsForm() {
    try {
      const s = await api("/api/settings/");
      $("#s-ai-key").value = s.ai?.api_key || "";
      $("#s-ai-model").value = s.ai?.model || "gpt-4o-mini";
      $("#s-ai-auto").checked = !!s.ai?.auto_reply_enabled;
      $("#s-tg-bot").value = s.bots?.telegram_bot_token || "";
      $("#s-bale-bot").value = s.bots?.bale_bot_token || "";
      $("#s-admins").value = (s.bots?.admin_chat_ids || []).join(",");
      $("#s-woo-on").checked = !!s.woocommerce?.enabled;
      $("#s-woo-url").value = s.woocommerce?.store_url || "";
      $("#s-woo-key").value = s.woocommerce?.consumer_key || "";
      $("#s-woo-secret").value = s.woocommerce?.consumer_secret || "";
      const ph = await api("/api/accounts/phone");
      if (ph.phone) $("#s-phone").value = ph.phone;
    } catch (e) {
      console.error(e);
    }
  }

  $("#btn-save-settings").onclick = async () => {
    const admins = $("#s-admins").value
      .split(",").map((x) => x.trim()).filter(Boolean)
      .map((x) => (isNaN(Number(x)) ? x : Number(x)));
    try {
      const phone = $("#s-phone").value.trim();
      if (phone) {
        await api("/api/accounts/phone", {
          method: "PUT",
          body: JSON.stringify({ phone }),
        });
      }
      await api("/api/settings/", {
        method: "PUT",
        body: JSON.stringify({
          data: {
            ai: {
              api_key: $("#s-ai-key").value,
              model: $("#s-ai-model").value,
              auto_reply_enabled: $("#s-ai-auto").checked,
              provider: "avalai",
            },
            bots: {
              telegram_bot_token: $("#s-tg-bot").value,
              bale_bot_token: $("#s-bale-bot").value,
              admin_chat_ids: admins,
            },
            woocommerce: {
              enabled: $("#s-woo-on").checked,
              store_url: $("#s-woo-url").value,
              consumer_key: $("#s-woo-key").value,
              consumer_secret: $("#s-woo-secret").value,
            },
          },
        }),
      });
      alert("ذخیره شد");
      closeSettings();
    } catch (e) {
      alert(e.message);
    }
  };

  $("#btn-woo-test").onclick = async () => {
    $("#woo-test-result").textContent = "در حال تست…";
    try {
      const r = await api("/api/settings/woocommerce/test", { method: "POST" });
      $("#woo-test-result").textContent = r.ok ? "اتصال موفق ✓" : "خطا: " + (r.error || "");
    } catch (e) {
      $("#woo-test-result").textContent = e.message;
    }
  };

  loadConversations();
  setInterval(loadConversations, 30000);
})();
