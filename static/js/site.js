'use strict';
(() => {
  const status = document.querySelector('#live-status');
  const announce = message => { if (status) status.textContent = message; };
  const toggle = document.querySelector('.mobile-toggle');
  toggle?.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    document.querySelector('#main-nav')?.classList.toggle('is-open', open);
  });
  const storageKey = 'little-rhymes-favorites-v1';
  function savedIds() {
    try {
      const ids = JSON.parse(localStorage.getItem(storageKey) || '[]');
      return Array.isArray(ids) ? [...new Set(ids.filter(id => /^\d{1,18}$/.test(String(id))).map(String))].slice(0, 100) : [];
    } catch { return []; }
  }
  function syncFavorites() {
    const ids = savedIds();
    document.querySelectorAll('[data-favorite]').forEach(button => {
      const selected = ids.includes(button.dataset.favorite);
      button.setAttribute('aria-pressed', String(selected));
      button.setAttribute('aria-label', selected ? 'Remove poem from favorites' : 'Save poem to favorites');
      button.textContent = button.classList.contains('favorite-button') ? (selected ? '♥' : '♡') : (selected ? '♥ Saved poem' : '♡ Save poem');
    });
  }
  document.addEventListener('click', event => {
    const button = event.target.closest('[data-favorite]');
    if (!button) return;
    let ids = savedIds();
    const id = button.dataset.favorite;
    const selected = ids.includes(id);
    if (!selected && ids.length >= 100) { announce('Your collection has 100 poems. Remove one before adding another.'); return; }
    ids = selected ? ids.filter(value => value !== id) : [...ids, id];
    try {
      localStorage.setItem(storageKey, JSON.stringify(ids));
      syncFavorites();
      announce(selected ? 'Poem removed from favorites.' : 'Poem saved on this browser.');
      if (favoriteList) renderFavorites();
    } catch { announce('Browser storage is unavailable. Favorites could not be saved.'); }
  });
  window.addEventListener('storage', () => { syncFavorites(); if (favoriteList) renderFavorites(); });
  syncFavorites();

  const favoriteList = document.querySelector('#favorites-list');
  let favoriteGeneration = 0;
  async function renderFavorites() {
    const generation = ++favoriteGeneration;
    const label = document.querySelector('#favorites-status');
    const ids = savedIds();
    favoriteList.replaceChildren();
    if (!ids.length) {
      label.textContent = 'Your little collection is waiting. Tap the heart on any poem to save it here.';
      const link = document.createElement('a'); link.href = '/poems/'; link.className = 'btn btn-primary'; link.textContent = 'Explore poems ↗'; favoriteList.append(link); return;
    }
    label.textContent = 'Gathering your little favorites…';
    try {
      let url = `${favoriteList.dataset.api}?ids=${encodeURIComponent(ids.join(','))}`;
      const poems = [];
      while (url) {
        const response = await fetch(url, {credentials: 'same-origin'});
        if (!response.ok) throw new Error('Could not load poems');
        const data = await response.json(); poems.push(...data.results); url = data.next;
        if (generation !== favoriteGeneration) return;
      }
      label.textContent = `${poems.length} little favorite${poems.length === 1 ? '' : 's'}. Some saved poems may be unavailable if they are no longer published.`;
      poems.forEach(poem => {
        const card = document.createElement('article'); card.className = 'poem-card favorite-result-card';
        const art = document.createElement('img'); art.src = poem.thumbnail || `/static/images/${poem.illustration}.svg`; art.alt = ''; art.className = 'favorite-result-art'; art.loading = 'lazy'; card.append(art);
        const body = document.createElement('div'); body.className = 'favorite-result';
        const language = document.createElement('small'); language.textContent = poem.language; body.append(language);
        const heading = document.createElement('h2'); const link = document.createElement('a'); link.href = poem.url; link.textContent = poem.title; heading.lang = poem.language_code; heading.dir = poem.text_direction; heading.append(link); body.append(heading);
        const description = document.createElement('p'); description.textContent = poem.short_description; body.append(description);
        const actions = document.createElement('div'); actions.className = 'card-actions';
        const read = document.createElement('a'); read.href = poem.url; read.textContent = 'Read poem ↗'; read.className = 'read-link'; actions.append(read);
        const remove = document.createElement('button'); remove.type = 'button'; remove.className = 'btn btn-small'; remove.dataset.favorite = String(poem.id); actions.append(remove);
        body.append(actions); card.append(body); favoriteList.append(card);
      });
      syncFavorites();
    } catch { if (generation === favoriteGeneration) label.textContent = 'We couldn’t load the poems. Refresh to try again. Your saved favorites are still on this browser.'; }
  }
  if (favoriteList) renderFavorites();

  document.querySelector('#print-poem')?.addEventListener('click', () => window.print());
  document.querySelector('#share-poem')?.addEventListener('click', async () => {
    const feedback = document.querySelector('#share-status');
    const url = document.querySelector('link[rel=canonical]')?.href || location.href;
    try {
      if (navigator.share) await navigator.share({title: document.title, url});
      else if (navigator.clipboard && window.isSecureContext) { await navigator.clipboard.writeText(url); feedback.textContent = 'Poem link copied!'; }
      else feedback.textContent = `Copy this poem link: ${url}`;
    } catch (error) { if (error.name !== 'AbortError') feedback.textContent = `Share this poem: ${url}`; }
  });
  document.querySelector('#poem-font-size')?.addEventListener('input', event => {
    document.querySelector('#poem-text').style.fontSize = `${Number(event.target.value)}px`;
  });
  document.querySelector('.load-video')?.addEventListener('click', event => {
    const holder = event.target.closest('[data-video-id]');
    if (!/^[A-Za-z0-9_-]{11}$/.test(holder.dataset.videoId)) return;
    const frame = document.createElement('iframe');
    frame.src = `https://www.youtube-nocookie.com/embed/${holder.dataset.videoId}?rel=0&playsinline=1`;
    frame.title = 'Poem video – YouTube privacy-enhanced player';
    frame.allow = 'encrypted-media; picture-in-picture; fullscreen';
    frame.allowFullscreen = true; frame.referrerPolicy = 'strict-origin-when-cross-origin';
    frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-presentation');
    holder.replaceWith(frame); frame.focus();
  });

})();
