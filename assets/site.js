/* 전생 거울 공통 기능 */
(function () {
  'use strict';

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

  var toastTimer;
  function toast(msg) {
    var el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('is-on');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove('is-on'); }, 2000);
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

  function share(opts) {
    if (navigator.share) {
      navigator.share({ title: opts.title, text: opts.text, url: opts.url }).catch(function () {});
    } else {
      copy(opts.text + '\n' + opts.url).then(
        function () { toast('결과와 링크를 복사했어요'); },
        function () { copyLink(opts.url); }
      );
    }
  }

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

  // 광고 코드가 없으면 광고 자리를 숨겨요
  document.addEventListener('DOMContentLoaded', function () {
    var box = document.getElementById('adBox');
    var slot = document.getElementById('adSlot');
    if (box && slot && !box.querySelector('*')) slot.hidden = true;
  });

  window.Site = {
    hash: hash, rng: rng, pick: pick, range: range, hasBatchim: hasBatchim,
    todayKey: todayKey, koreanDate: koreanDate,
    toast: toast, copy: copy, copyLink: copyLink, share: share,
    baseUrl: baseUrl, setQuery: setQuery,
    storeGet: storeGet, storeSet: storeSet,
    reduceMotion: reduceMotion
  };
})();
