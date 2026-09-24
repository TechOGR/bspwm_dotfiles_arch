/* TechOGR login - lightdm-webkit2-greeter theme logic
 * Users, sessions and power come from the greeter's `lightdm` object;
 * the look (colors, texts, wallpaper, avatar) from data/config.js,
 * written by BetterLock. Opened in a normal browser it runs on a small
 * mock (password "test") to try the theme. */
(function () {
	'use strict';

	const C = Object.assign({
		accent: '#7aa2f7', accent2: '#bb9af7', fg: '#c0caf5', verify: '#9ece6a', wrong: '#f7768e',
		bg: '#1a1b26', black: '#15161e', cardAlpha: 55, radius: 28, pos: 'center', card: true,
		avatar: true, shape: 'circle', user: '', name: '', greeter: 'Type your password',
		message: '', clock: '%H:%M', date: '%A, %d %B', rice: 'crackone', lang: '', stamp: 0,
	}, window.TECHOGR || {});

	const $ = (id) => document.getElementById(id);
	const body = document.body;
	const store = {
		get(k) { try { return localStorage.getItem('techogr.' + k); } catch (e) { return null; } },
		set(k, v) { try { localStorage.setItem('techogr.' + k, v); } catch (e) { /* no storage */ } },
	};

	// ───────────────────────────────────────────── browser preview mock
	if (!window.lightdm) {
		const me = C.user || 'user';
		window.lightdm = {
			hostname: 'preview', in_authentication: false, is_authenticated: false,
			authentication_user: null, default_session: 'bspwm', select_user_hint: null,
			can_suspend: true, can_restart: true, can_shutdown: true,
			users: [{ username: me, display_name: me, image: '', session: 'bspwm' },
				{ username: 'guest', display_name: 'Guest', image: '', session: '' }],
			sessions: [{ key: 'bspwm', name: 'BSPWM' }, { key: 'xfce', name: 'Xfce Session' },
				{ key: 'i3', name: 'i3' }],
			authenticate(u) { this.in_authentication = true; this.authentication_user = u; setTimeout(() => window.show_prompt('Password: ', 1), 30); },
			cancel_authentication() { this.in_authentication = false; },
			respond(p) {
				setTimeout(() => { this.is_authenticated = p === 'test'; this.in_authentication = false; window.authentication_complete(); }, 900);
			},
			start_session_sync(k) { alert('start session: ' + k); return true; },
			suspend() { alert('suspend'); }, restart() { alert('restart'); }, shutdown() { alert('shutdown'); },
		};
	}
	const LD = window.lightdm;

	// ───────────────────────────────────────────── look
	function rgb(hex) {
		const m = /^#?([0-9a-f]{6})$/i.exec(hex || '');
		if (!m) return null;
		const n = parseInt(m[1], 16);
		return [(n >> 16) & 255, (n >> 8) & 255, n & 255].join(', ');
	}

	function applyLook() {
		const r = document.documentElement.style;
		for (const k of ['accent', 'accent2', 'fg', 'verify', 'wrong', 'bg', 'black']) {
			const v = rgb(C[k]);
			if (!v) continue;
			r.setProperty('--' + k, C[k]);
			r.setProperty('--' + k + '-rgb', v);
		}
		r.setProperty('--card-alpha', Math.max(0, Math.min(95, +C.cardAlpha || 0)) / 100);
		r.setProperty('--radius', Math.max(0, Math.min(80, +C.radius || 0)));
		r.setProperty('--fx', { left: '27%', right: '73%' }[C.pos] || '50%');
		if (C.stamp) {
			const q = '?v=' + C.stamp;
			$('bg').style.backgroundImage = `url("data/background.jpg${q}")`;
			r.setProperty('--frost', `url("data/frost.jpg${q}")`);
		}
		body.classList.toggle('nocard', !C.card);
		body.classList.toggle('noavatar', !C.avatar);
		body.classList.add('shape-' + (C.shape || 'circle'));
		$('pass').placeholder = C.greeter;
		const host = LD.hostname || '';
		$('foot-left').innerHTML = `<span class="ico">󰣇</span>  ${esc(host)}  ·  ${esc(C.rice)}`;
		$('foot-mid').textContent = C.message || '';
		scale();
	}

	function scale() {
		const s = Math.max(0.6, Math.min(2.5, Math.min(innerWidth / 1920, innerHeight / 1080)));
		document.documentElement.style.setProperty('--s', s);
	}

	function esc(t) {
		return String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
	}

	// ───────────────────────────────────────────── clock (strftime subset)
	const locale = (C.lang || navigator.language || 'en').replace('_', '-').split('.')[0];

	function fmt(pattern, d) {
		const pad = (n) => String(n).padStart(2, '0');
		const name = (opt) => { try { return d.toLocaleDateString(locale, opt); } catch (e) { return d.toLocaleDateString('en', opt); } };
		const map = {
			H: () => pad(d.getHours()), M: () => pad(d.getMinutes()), S: () => pad(d.getSeconds()),
			I: () => pad(d.getHours() % 12 || 12), l: () => String(d.getHours() % 12 || 12),
			p: () => (d.getHours() < 12 ? 'AM' : 'PM'), P: () => (d.getHours() < 12 ? 'am' : 'pm'),
			A: () => name({ weekday: 'long' }), a: () => name({ weekday: 'short' }),
			B: () => name({ month: 'long' }), b: () => name({ month: 'short' }), h: () => name({ month: 'short' }),
			d: () => pad(d.getDate()), e: () => String(d.getDate()), m: () => pad(d.getMonth() + 1),
			Y: () => String(d.getFullYear()), y: () => pad(d.getFullYear() % 100), '%': () => '%',
		};
		return pattern.replace(/%([a-zA-Z%])/g, (all, k) => (map[k] ? map[k]() : all));
	}

	function tick() {
		const d = new Date();
		$('time').textContent = fmt(C.clock, d);
		$('date').textContent = fmt(C.date, d);
	}

	// ───────────────────────────────────────────── users
	const users = (LD.users || []).slice();
	let idx = 0;
	let manual = false;

	function pickFirstUser() {
		const want = [LD.select_user_hint, store.get('user'), C.user];
		for (const w of want) {
			const i = users.findIndex((u) => u.username === w);
			if (w && i >= 0) return i;
		}
		return 0;
	}

	function currentName() {
		if (manual || !users.length) return $('name-input').value.trim();
		return users[idx].username;
	}

	function displayName(u) {
		if (u.username === C.user && C.name) return C.name;
		const n = u.display_name || u.username;
		return n === u.username ? n.charAt(0).toUpperCase() + n.slice(1) : n;
	}

	function setAvatar(username, image) {
		const box = $('avatar');
		const img = $('avatar-img');
		const tries = [];
		if (username) tries.push(`data/avatar-${username}.png?v=${C.stamp}`);
		if (image) tries.push(image.startsWith('/') ? 'file://' + image : image);
		box.classList.remove('has-img');
		const next = () => {
			const src = tries.shift();
			if (!src) { img.removeAttribute('src'); return; }
			img.onload = () => box.classList.add('has-img');
			img.onerror = next;
			img.src = src;
		};
		next();
	}

	function showUser() {
		body.classList.toggle('manual', manual || !users.length);
		body.classList.toggle('single', users.length < 1);
		const host = LD.hostname || 'localhost';
		if (manual || !users.length) {
			const n = $('name-input').value.trim();
			$('host').textContent = `󰀄  ${n || 'user'}@${host}`;
			setAvatar(n, '');
			return;
		}
		const u = users[idx];
		$('name').textContent = displayName(u);
		$('host').textContent = `󰀄  ${u.username}@${host}`;
		setAvatar(u.username, u.image);
		if (u.session && sessions.some((s) => s.key === u.session)) setSession(u.session);
	}

	function stepUser(dir) {
		const n = users.length + 1;              // + "other user"
		let pos = manual ? users.length : idx;
		pos = (pos + dir + n) % n;
		manual = pos === users.length;
		if (!manual) idx = pos;
		cancelAuth();
		clearStatus();
		showUser();
		(manual ? $('name-input') : $('pass')).focus();
		if (!manual) beginAuth();
	}

	// ───────────────────────────────────────────── sessions
	const sessions = (LD.sessions || []).slice();
	let session = '';

	function setSession(key) {
		const s = sessions.find((x) => x.key === key) || sessions[0];
		if (!s) { $('session').style.display = 'none'; return; }
		session = s.key;
		$('session-name').textContent = s.name;
		for (const li of $('session-list').children) li.classList.toggle('selected', li.dataset.key === session);
	}

	function buildSessions() {
		const list = $('session-list');
		for (const s of sessions) {
			const li = document.createElement('li');
			li.dataset.key = s.key;
			li.textContent = s.name;
			li.addEventListener('click', (e) => {
				e.stopPropagation();
				setSession(s.key);
				store.set('session', s.key);
				$('session').classList.remove('open');
				$('pass').focus();
			});
			list.appendChild(li);
		}
		const want = [store.get('session'), LD.default_session, 'bspwm'];
		setSession(want.find((k) => k && sessions.some((s) => s.key === k)) || (sessions[0] || {}).key);
		$('session-btn').addEventListener('click', (e) => {
			e.stopPropagation();
			$('session').classList.toggle('open');
		});
		document.addEventListener('click', () => $('session').classList.remove('open'));
	}

	// ───────────────────────────────────────────── authentication
	let authUser = null;
	let promptReady = false;
	let pending = null;
	let busy = false;

	function cancelAuth() {
		if (LD.in_authentication) { try { LD.cancel_authentication(); } catch (e) { /* ignore */ } }
		authUser = null;
		promptReady = false;
	}

	function beginAuth() {
		const name = currentName();
		cancelAuth();
		if (!name) return;
		authUser = name;
		LD.authenticate(name);
	}

	window.show_prompt = function (text, type) {
		// type 1 = secret (the password); a question here would be "login:"
		if (pending !== null) {
			const p = pending;
			pending = null;
			LD.respond(p);
		} else {
			promptReady = true;
		}
	};

	window.show_message = function (text, type) {
		if (text) setStatus(text, type === 1 ? 'wrong' : '');
	};

	window.authentication_complete = function () {
		busy = false;
		if (LD.is_authenticated) {
			store.set('user', authUser || currentName());
			store.set('session', session);
			setStatus('󰄬  Welcome', 'verify');
			body.classList.add('leaving');
			setTimeout(startSession, 550);
		} else {
			body.classList.remove('verifying');
			body.classList.add('wrong');
			setStatus('󰀦  Wrong password', 'wrong');
			$('pass').value = '';
			$('pass').focus();
			setTimeout(() => body.classList.remove('wrong'), 900);
			beginAuth();
		}
	};

	window.autologin_timer_expired = function () { /* no autologin */ };

	function startSession() {
		let ok;
		try {
			if (LD.start_session_sync) ok = LD.start_session_sync(session);
			else if (LD.start_session) ok = LD.start_session(session);
			else ok = LD.login(LD.authentication_user, session);
		} catch (e) {
			ok = false;
		}
		if (ok === false) {
			body.classList.remove('leaving', 'verifying');
			setStatus('󰀦  Could not start ' + session, 'wrong');
			beginAuth();
		}
	}

	function submit(e) {
		if (e) e.preventDefault();
		if (busy) return;
		const name = currentName();
		if (!name) { $('name-input').focus(); return; }
		const pw = $('pass').value;
		busy = true;
		body.classList.remove('wrong');
		body.classList.add('verifying');
		setStatus('󰦖  Verifying…', 'verify');
		if (LD.in_authentication && authUser === name && promptReady) {
			promptReady = false;
			LD.respond(pw);
		} else {
			pending = pw;
			beginAuth();
		}
	}

	// ───────────────────────────────────────────── status + ring
	function setStatus(text, cls) {
		const s = $('status');
		s.textContent = text;
		s.className = cls || '';
	}

	function clearStatus() { setStatus('', ''); }

	const hl = $('ring-hl');

	function flash(color) {
		const angle = Math.floor(Math.random() * 360);
		hl.style.stroke = color;
		hl.style.strokeOpacity = '1';
		hl.style.transform = `rotate(${angle}deg)`;
		clearTimeout(flash.t);
		flash.t = setTimeout(() => { hl.style.strokeOpacity = '0'; }, 450);
	}

	function capsWarning(e) {
		if (busy || !e.getModifierState) return;
		const s = $('status');
		if (e.getModifierState('CapsLock')) setStatus('󰘲  Caps Lock', 'caps');
		else if (s.className === 'caps') clearStatus();
	}

	// ───────────────────────────────────────────── power (click twice)
	function power(id, can, action, label) {
		const b = $(id);
		if (!LD[can]) { b.hidden = true; return; }
		b.addEventListener('click', (e) => {
			e.stopPropagation();
			if (b.dataset.armed) { LD[action](); return; }
			b.dataset.armed = '1';
			b.style.color = 'var(--wrong)';
			setStatus(`Click again to ${label}`, 'caps');
			setTimeout(() => { delete b.dataset.armed; b.style.color = ''; if ($('status').className === 'caps') clearStatus(); }, 3000);
		});
	}

	// ───────────────────────────────────────────── wiring
	function init() {
		applyLook();
		tick();
		setInterval(tick, 1000);
		addEventListener('resize', scale);

		buildSessions();
		idx = pickFirstUser();
		manual = !users.length;
		showUser();

		$('pill').addEventListener('submit', submit);
		$('user-prev').addEventListener('click', () => stepUser(-1));
		$('user-next').addEventListener('click', () => stepUser(1));
		$('name').addEventListener('click', () => { manual = true; $('name-input').value = ''; cancelAuth(); showUser(); $('name-input').focus(); });
		$('name-input').addEventListener('input', () => showUser());
		$('name-input').addEventListener('keydown', (e) => {
			if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); $('pass').focus(); }
		});

		$('pass').addEventListener('keydown', (e) => {
			capsWarning(e);
			if (e.key === 'Backspace' || e.key === 'Delete') flash(C.wrong);
			else if (e.key === 'Escape') { $('pass').value = ''; flash(C.wrong); }
			else if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && !$('pass').value) { e.preventDefault(); stepUser(e.key === 'ArrowUp' ? -1 : 1); }
			else if (e.key.length === 1) {
				flash(C.accent);
				if (body.classList.contains('wrong')) { body.classList.remove('wrong'); clearStatus(); }
			}
		});
		$('pass').addEventListener('keyup', capsWarning);

		// typing anywhere goes to the password field
		document.addEventListener('keydown', (e) => {
			const a = document.activeElement;
			if (e.key === 'Escape') $('session').classList.remove('open');
			if (a && (a.id === 'pass' || a.id === 'name-input')) return;
			if (e.key.length === 1 || e.key === 'Enter' || e.key === 'Backspace') $('pass').focus();
		});

		power('pw-suspend', 'can_suspend', 'suspend', 'suspend');
		power('pw-restart', 'can_restart', 'restart', 'restart');
		power('pw-shutdown', 'can_shutdown', 'shutdown', 'shut down');

		(manual ? $('name-input') : $('pass')).focus();
		if (!manual) beginAuth();
		requestAnimationFrame(() => body.classList.remove('loading'));
	}

	try {
		init();
	} catch (e) {
		body.classList.remove('loading');
		setStatus('Theme error: ' + e.message, 'wrong');
		throw e;
	}
})();
