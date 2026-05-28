// Minimal chatbot frontend with suggestions, timestamps, and typing feedback.
(function(){
  const apiUrl = '/chatbot/api/message/';
  const toggle = document.getElementById('chatbot-toggle');
  const panel = document.getElementById('chatbot-panel');
  const closeBtn = document.getElementById('chatbot-close');
  const form = document.getElementById('chatbot-form');
  const input = document.getElementById('chatbot-input');
  const messages = document.getElementById('chatbot-messages');
  const suggestions = document.getElementById('chatbot-suggestions');
  let greeted = false;

  if(!toggle || !panel) return;

  function formatTime(date){
    return date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }

  function appendMessage(text, who='bot'){
    const el = document.createElement('div');
    el.className = 'chatbot-msg ' + (who==='user' ? 'user' : 'bot');
    el.textContent = text;
    el.dataset.time = formatTime(new Date());
    messages.appendChild(el);
    messages.scrollTop = messages.scrollHeight;
  }

  function renderSuggestions(items){
    suggestions.innerHTML = '';
    if(!Array.isArray(items) || !items.length){
      suggestions.hidden = true;
      return;
    }
    suggestions.hidden = false;
    items.forEach(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'chatbot-suggestion-btn';
      const label = typeof item === 'string' ? item : item.label || '';
      button.textContent = label;
      if(item && item.url){
        button.addEventListener('click', ()=>{
          if(item.goDirect){
            window.location.href = item.url;
            return;
          }
          input.value = label;
          input.focus();
          appendMessage(label, 'user');
          sendMessage({message: label, url: item.url});
        });
      } else {
        button.addEventListener('click', ()=>{
          input.value = label;
          input.focus();
          appendMessage(label, 'user');
          sendMessage({message: label});
        });
      }
      suggestions.appendChild(button);
    });
  }

  function getCookie(name){
    const v = document.cookie.match('(^|;)\\s*'+name+'\\s*=\\s*([^;]+)');
    return v ? v.pop() : '';
  }

  async function sendMessage(payload){
    renderSuggestions([]);
    try{
      const res = await fetch(apiUrl, {
        method:'POST',
        headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},
        body:JSON.stringify(payload),
      });
      if(!res.ok){
        appendMessage('Sorry, I could not reach the chatbot right now. Try again later.');
        return;
      }
      const data = await res.json();
      if(data.reply) appendMessage(data.reply, 'bot');
      renderSuggestions(data.suggestions);
    }catch(e){
      appendMessage('An error occurred while contacting the chatbot.');
    }
  }

  function openPanel(){
    panel.setAttribute('aria-hidden','false');
    input.focus();
    if(!greeted){
      sendMessage({type:'init', message:''});
      greeted = true;
    }
  }

  function closePanel(){
    panel.setAttribute('aria-hidden','true');
  }

  function togglePanel(){
    const hidden = panel.getAttribute('aria-hidden') === 'true';
    if(hidden){
      openPanel();
    } else {
      closePanel();
    }
  }

  toggle.addEventListener('click', togglePanel);
  closeBtn.addEventListener('click', closePanel);

  form.addEventListener('submit', (ev)=>{
    ev.preventDefault();
    const text = input.value.trim();
    if(!text) return;
    appendMessage(text,'user');
    input.value = '';
    sendMessage({message:text});
  });
})();
