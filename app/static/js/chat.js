/**
 * chat.js — Chat panel UI, SSE streaming, entity link → map navigation
 */

(function () {
  'use strict';

  const MAX_MESSAGE_LENGTH = 2000;
  const MAX_VISIBLE_HISTORY = 50;
  const API_HISTORY_LIMIT = 10;

  let chatOpen = false;
  let isStreaming = false;
  let conversationHistory = []; // {role, content}
  let welcomeShown = false;

  // DOM refs (set on DOMContentLoaded)
  let toggleBtn, panel, minimizeBtn, messagesEl, inputEl, sendBtn;

  // === Initialisation ===

  function init() {
    toggleBtn = document.getElementById('chat-toggle');
    panel = document.getElementById('chat-panel');
    minimizeBtn = document.getElementById('chat-minimize');
    messagesEl = document.getElementById('chat-messages');
    inputEl = document.getElementById('chat-input');
    sendBtn = document.getElementById('chat-send');

    if (!toggleBtn || !panel) return; // Guard if elements missing

    toggleBtn.addEventListener('click', toggleChat);
    minimizeBtn.addEventListener('click', toggleChat);
    sendBtn.addEventListener('click', () => sendMessage());

    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });

    inputEl.addEventListener('input', autoResizeTextarea);
  }

  // === Toggle Chat ===

  function toggleChat() {
    chatOpen = !chatOpen;
    if (chatOpen) {
      panel.classList.remove('chat-closed');
      panel.classList.add('chat-open');
      toggleBtn.style.display = 'none';
      if (!welcomeShown) {
        renderWelcome();
        welcomeShown = true;
      }
      inputEl.focus();
    } else {
      panel.classList.remove('chat-open');
      panel.classList.add('chat-closed');
      toggleBtn.style.display = 'flex';
    }
  }

  // === Welcome Message ===

  function renderWelcome() {
    const suggestions = [
      'Which boroughs should we prioritise?',
      'What drives risk in Hackney?',
      'Compare Barking and Richmond',
      'Give me a London overview',
    ];

    const div = document.createElement('div');
    div.className = 'chat-msg assistant';
    div.innerHTML = `
      <div class="chat-welcome">
        <h3>Policy Assistant</h3>
        <p>Ask me about mental health need across London's neighbourhoods.</p>
        <div class="chat-suggestions">
          ${suggestions.map(s => `<button class="chat-suggestion">${s}</button>`).join('')}
        </div>
      </div>
    `;

    messagesEl.appendChild(div);

    // Bind suggestion clicks
    div.querySelectorAll('.chat-suggestion').forEach(btn => {
      btn.addEventListener('click', () => {
        inputEl.value = btn.textContent;
        sendMessage();
      });
    });
  }

  // === Send Message ===

  async function sendMessage(text) {
    text = text || inputEl.value.trim();
    if (!text || isStreaming) return;

    // Truncate
    if (text.length > MAX_MESSAGE_LENGTH) {
      text = text.slice(0, MAX_MESSAGE_LENGTH);
    }

    // Show user message
    appendMessage('user', text);
    inputEl.value = '';
    autoResizeTextarea();

    // Add to history
    conversationHistory.push({ role: 'user', content: text });

    // Prepare API history (last N turns)
    const apiHistory = conversationHistory
      .slice(-(API_HISTORY_LIMIT * 2))
      .slice(0, -1); // Exclude current message (sent separately)

    // Start streaming
    isStreaming = true;
    sendBtn.disabled = true;

    // Create assistant message container with typing dots
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-msg assistant';
    msgDiv.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    messagesEl.appendChild(msgDiv);
    scrollToBottom();

    let fullText = '';

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history: apiHistory }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let firstToken = true;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = parseSSE(buffer);
        buffer = events.remaining;

        for (const event of events.parsed) {
          if (event.type === 'token') {
            if (firstToken) {
              msgDiv.innerHTML = ''; // Clear typing dots
              firstToken = false;
            }
            fullText += event.data.text;
            msgDiv.textContent = fullText;
            scrollToBottom();
          }
          // context event — could be used for pre-highlighting, ignored for now
        }
      }
    } catch (err) {
      console.error('Chat error:', err);
      if (!fullText) {
        msgDiv.innerHTML = '<span class="chat-error">Connection lost. Please try again.</span>';
      }
    }

    // Post-process: markdown-light + entity links
    if (fullText) {
      msgDiv.innerHTML = renderMarkdown(fullText);
      postProcessMessage(msgDiv);
      conversationHistory.push({ role: 'assistant', content: fullText });
    }

    // Trim visible history
    while (messagesEl.children.length > MAX_VISIBLE_HISTORY) {
      messagesEl.removeChild(messagesEl.firstChild);
    }

    isStreaming = false;
    sendBtn.disabled = false;
    scrollToBottom();
  }

  // === SSE Parser ===

  function parseSSE(buffer) {
    const parsed = [];
    const lines = buffer.split('\n');
    let remaining = '';
    let currentType = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.startsWith('event: ')) {
        currentType = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          parsed.push({ type: currentType || 'message', data });
        } catch {
          // incomplete JSON, put back
          remaining = lines.slice(i).join('\n');
          return { parsed, remaining };
        }
        currentType = null;
      } else if (line === '' ) {
        // Event boundary — reset
        currentType = null;
      } else {
        // Incomplete line — could be partial, keep in buffer
        remaining = lines.slice(i).join('\n');
        return { parsed, remaining };
      }
    }

    return { parsed, remaining };
  }

  // === Light Markdown Renderer ===

  function renderMarkdown(text) {
    // Escape HTML
    let html = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // Paragraphs (double newline)
    html = html
      .split(/\n\n+/)
      .map(para => {
        para = para.trim();
        if (!para) return '';
        // Check if paragraph is a list
        if (/^[\s]*[-*\d+.]\s/m.test(para)) {
          const items = para.split(/\n/).map(line => {
            const content = line.replace(/^[\s]*[-*]\s+/, '').replace(/^\d+\.\s+/, '');
            return `<li>${content}</li>`;
          }).join('');
          return `<ul>${items}</ul>`;
        }
        return `<p>${para.replace(/\n/g, '<br>')}</p>`;
      })
      .join('');

    return html;
  }

  // === Entity Link Post-Processing ===

  function postProcessMessage(container) {
    let html = container.innerHTML;

    // Replace [[borough:Name]] with clickable spans
    html = html.replace(
      /\[\[borough:(.+?)\]\]/g,
      '<span class="chat-link chat-borough" data-borough="$1">$1</span>'
    );

    // Replace [[lsoa:CODE|Display]] with clickable spans
    html = html.replace(
      /\[\[lsoa:(\w+)\|(.+?)\]\]/g,
      '<span class="chat-link chat-lsoa" data-lsoa="$1">$2</span>'
    );

    container.innerHTML = html;

    // Bind borough clicks
    container.querySelectorAll('.chat-borough').forEach(el => {
      el.addEventListener('click', () => {
        handleBoroughClick(el.dataset.borough);
      });
    });

    // Bind LSOA clicks
    container.querySelectorAll('.chat-lsoa').forEach(el => {
      el.addEventListener('click', () => {
        handleLSOAClick(el.dataset.lsoa);
      });
    });
  }

  // === Map Navigation Handlers ===

  function handleBoroughClick(boroughName) {
    const select = document.getElementById('borough-select');
    if (!select) return;

    // Find matching option (case-insensitive)
    const option = Array.from(select.options).find(
      opt => opt.value.toLowerCase() === boroughName.toLowerCase()
    );

    if (option) {
      select.value = option.value;
      select.dispatchEvent(new Event('change'));
    }
  }

  function handleLSOAClick(lsoaCode) {
    if (!window.APP || !window.APP.geojsonData) return;

    const feature = window.APP.geojsonData.features.find(
      f => f.properties.lsoa_code === lsoaCode
    );

    if (feature) {
      const bounds = L.geoJSON(feature).getBounds();
      window.APP.map.fitBounds(bounds, { padding: [100, 100], maxZoom: 15 });
      window.showLSOADetail(feature.properties);
    }
  }

  // === Utilities ===

  function appendMessage(role, content) {
    const div = document.createElement('div');
    div.className = `chat-msg ${role}`;
    div.textContent = content;
    messagesEl.appendChild(div);
    scrollToBottom();
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function autoResizeTextarea() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 72) + 'px';
  }

  // === Start ===

  document.addEventListener('DOMContentLoaded', init);
})();
