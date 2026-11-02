/* 전생 거울 공통 기능 */
(function () {
  'use strict';

  var CONFIG = {
    // 카카오 개발자 사이트(developers.kakao.com)에서 받은 JavaScript 키를 넣으면
    // 공유 창에 카카오톡 버튼이 생겨요. 비워 두면 카카오톡 버튼은 숨겨져요.
    kakaoKey: '',
    kakaoSdk: 'https://t1.kakaocdn.net/kakao_js_sdk/2.8.3/kakao.min.js'
  };

  /* ── 결과 계산 ─────────────────────────────── */
  function hash(str) {
    var h = 0x811c9dc5;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 0x01000193);
    }
    h ^= h >>> 16; h = Math.imul(h, 0x85ebca6b);
    h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35);
    h ^= h >>> 16;
    return h >>> 0;
  }

  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function pick(r, arr) { return arr[Math.floor(r() * arr.length)]; }
  function range(r, min, max) { return min + Math.floor(r() * (max - min + 1)); }

  function hasBatchim(word) {
    var c = word.charCodeAt(word.length - 1);
    if (c < 0xAC00 || c > 0xD7A3) return false;
    return (c - 0xAC00) % 28 !== 0;
  }

  function todayKey(d) {
    d = d || new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  function koreanDate(d) {
    return (d || new Date()).toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  /* ── 생년월일 입력 (숫자로 입력) ─────────────────────────────── */
  function birthInput(el) {
    if (!el) return;
    el.addEventListener('input', function () {
      var d = el.value.replace(/\D/g, '').slice(0, 8);
      el.value = d.length === 8 ? d.slice(0, 4) + '.' + d.slice(4, 6) + '.' + d.slice(6) : d;
    });
  }

  // 결과: { empty: true } | { error: '...' } | { iso: 'YYYY-MM-DD' }
  function parseBirth(value) {
    var d = String(value || '').replace(/\D/g, '');
    if (!d) return { empty: true };
    if (d.length === 6) {
      var yy = Number(d.slice(0, 2));
      var cur = new Date().getFullYear() % 100;
      d = (yy > cur ? '19' : '20') + d;
    }
    if (d.length !== 8) return { error: '생년월일을 숫자 8자리로 입력해 주세요. 예: 19980417' };
    var y = Number(d.slice(0, 4)), m = Number(d.slice(4, 6)), day = Number(d.slice(6, 8));
    var dt = new Date(y, m - 1, day);
    if (y < 1900 || dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== day) {
      return { error: '없는 날짜예요. 생년월일을 다시 확인해 주세요.' };
    }
    var iso = d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6, 8);
    if (iso > todayKey()) return { error: '생년월일은 오늘 이전 날짜로 입력해 주세요.' };
    return { iso: iso };
  }

  /* ── 알림 ─────────────────────────────── */
  var toastTimer;
  function toast(msg) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove('is-on'); }, 2200);
  }

  function copy(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy') ? resolve() : reject(); } catch (e) { reject(e); }
      document.body.removeChild(ta);
    });
  }

  function copyLink(url) {
    copy(url).then(
      function () { toast('링크를 복사했어요'); },
      function () { toast('복사하지 못했어요. 주소창의 링크를 길게 눌러 복사해 주세요'); }
    );
  }

  /* ── 카카오톡 ─────────────────────────────── */
  function kakaoReady() {
    try {
      if (!CONFIG.kakaoKey || !window.Kakao) return false;
      if (!window.Kakao.isInitialized()) window.Kakao.init(CONFIG.kakaoKey);
      return window.Kakao.isInitialized();
    } catch (e) { return false; }
  }

  function loadKakao() {
    if (!CONFIG.kakaoKey || window.Kakao) return;
    var s = document.createElement('script');
    s.src = CONFIG.kakaoSdk;
    s.crossOrigin = 'anonymous';
    s.async = true;
    s.onload = kakaoReady;
    document.head.appendChild(s);
  }

  /* ── 공유 창 ─────────────────────────────── */
  var ICONS = {
    kakao: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="#3C1E1E" d="M12 4.2c-5 0-9 3.1-9 6.9 0 2.4 1.6 4.5 4.1 5.8l-.8 3.1c-.1.4.3.6.6.4l3.7-2.5c.5.1.9.1 1.4.1 5 0 9-3.1 9-6.9S17 4.2 12 4.2z"/></svg>',
    sms: '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round" d="M4 5.5h16v10.5H9.5L5 19.5V16H4z"/></svg>',
    copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></g></svg>',
    more: '<svg viewBox="0 0 24 24" aria-hidden="true"><g fill="#fff"><circle cx="5.5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="18.5" cy="12" r="2"/></g></svg>'
  };

  var sheet, lastFocus, shareData;

  function item(kind, label, bg, icon, isLink) {
    var tag = isLink ? 'a' : 'button';
    var attrs = isLink ? ' target="_blank" rel="noopener"' : ' type="button"';
    return '<' + tag + ' class="share-item" data-kind="' + kind + '"' + attrs + '>' +
      '<span class="share-icon" style="background:' + bg + '">' + icon + '</span>' + label + '</' + tag + '>';
  }

  function buildSheet() {
    sheet = document.createElement('div');
    sheet.className = 'share';
    sheet.hidden = true;
    sheet.innerHTML =
      '<div class="share-backdrop" data-close></div>' +
      '<div class="share-panel" role="dialog" aria-modal="true" aria-labelledby="shareTitle">' +
        '<h2 class="share-title" id="shareTitle">어디로 공유할까요?</h2>' +
        '<div class="share-grid">' +
          item('kakao', '카카오톡', '#FEE500', ICONS.kakao) +
          item('sms', '메시지', '#34A853', ICONS.sms, true) +
          item('x', 'X', '#111', '<span>X</span>', true) +
          item('threads', '스레드', '#111', '<span>@</span>', true) +
          item('facebook', '페이스북', '#1877F2', '<span>f</span>', true) +
          item('copy', '복사하기', '#6B5E52', ICONS.copy) +
          item('more', '더보기', '#8A8F98', ICONS.more) +
        '</div>' +
        '<button type="button" class="btn btn-ghost share-close" data-close>닫기</button>' +
      '</div>';
    document.body.appendChild(sheet);

    sheet.addEventListener('click', function (e) {
      if (e.target.closest('[data-close]')) { closeShare(); return; }
      var el = e.target.closest('.share-item');
      if (!el || !shareData) return;
      var kind = el.dataset.kind;
      if (kind === 'kakao') { e.preventDefault(); shareKakao(); }
      else if (kind === 'copy') {
        copy(shareData.text + '\n' + shareData.url).then(
          function () { toast('결과와 링크를 복사했어요. 원하는 곳에 붙여 넣어 주세요'); },
          function () { copyLink(shareData.url); }
        );
      } else if (kind === 'more') {
        navigator.share({ title: shareData.title, text: shareData.text, url: shareData.url }).catch(function () {});
      }
      setTimeout(closeShare, 60);
    });

    document.addEventListener('keydown', function (e) {
      if (!sheet.hidden && e.key === 'Escape') closeShare();
    });
  }

  function shareKakao() {
    if (!kakaoReady()) { toast('카카오톡을 불러오는 중이에요. 잠시 후 다시 눌러 주세요'); loadKakao(); return; }
    var d = shareData;
    try {
      window.Kakao.Share.sendDefault({
        objectType: 'feed',
        content: {
          title: d.title,
          description: d.text,
          imageUrl: d.image,
          link: { mobileWebUrl: d.url, webUrl: d.url }
        },
        buttons: [
          { title: '결과 보기', link: { mobileWebUrl: d.url, webUrl: d.url } },
          { title: '나도 해 보기', link: { mobileWebUrl: d.home, webUrl: d.home } }
        ]
      });
    } catch (e) {
      toast('카카오톡 공유를 열지 못했어요. 복사하기로 보내 주세요');
    }
  }

  function share(opts) {
    if (!sheet) buildSheet();
    var og = document.querySelector('meta[property="og:image"]');
    shareData = {
      title: opts.title,
      text: opts.text,
      url: opts.url,
      home: baseUrl(),
      image: opts.image || (og ? og.content : '')
    };
    var both = opts.text + '\n' + opts.url;
    var links = {
      sms: 'sms:?&body=' + encodeURIComponent(both),
      x: 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(opts.text) + '&url=' + encodeURIComponent(opts.url),
      threads: 'https://www.threads.net/intent/post?text=' + encodeURIComponent(opts.text + ' ' + opts.url),
      facebook: 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(opts.url)
    };
    Object.keys(links).forEach(function (k) {
      sheet.querySelector('[data-kind="' + k + '"]').href = links[k];
    });
    sheet.querySelector('[data-kind="kakao"]').hidden = !CONFIG.kakaoKey;
    sheet.querySelector('[data-kind="more"]').hidden = !navigator.share;

    lastFocus = document.activeElement;
    sheet.hidden = false;
    document.documentElement.style.overflow = 'hidden';
    var first = sheet.querySelector('.share-item:not([hidden])');
    if (first) first.focus();
  }

  function closeShare() {
    if (!sheet || sheet.hidden) return;
    sheet.hidden = true;
    document.documentElement.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* ── 주소 ─────────────────────────────── */
  function baseUrl() {
    return location.href.split('?')[0].split('#')[0];
  }

  function setQuery(query) {
    try { history.replaceState(null, '', baseUrl() + (query ? '?' + query : '')); } catch (e) {}
  }

  function storeGet(key) {
    try { return JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) { return null; }
  }
  function storeSet(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
  }

  var reduceMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  document.addEventListener('DOMContentLoaded', function () {
    // 광고 코드가 없으면 광고 자리를 숨겨요
    var box = document.getElementById('adBox');
    var slot = document.getElementById('adSlot');
    if (box && slot && !box.querySelector('*')) slot.hidden = true;
    loadKakao();
  });

  window.Site = {
    hash: hash, rng: rng, pick: pick, range: range, hasBatchim: hasBatchim,
    todayKey: todayKey, koreanDate: koreanDate,
    birthInput: birthInput, parseBirth: parseBirth,
    toast: toast, copy: copy, copyLink: copyLink, share: share,
    baseUrl: baseUrl, setQuery: setQuery,
    storeGet: storeGet, storeSet: storeSet,
    reduceMotion: reduceMotion
  };
})();
