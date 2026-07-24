// Mini "backend" v2 para la demo funcional.
// Modelo por-servicio: cada servicio de un turno tiene su propio
// especialista y estado. Un especialista puede pertenecer a varias
// áreas. Historial de servicios finalizados. Cambio de especialista
// autorizado con PIN de admin + motivo.
(function () {
  const KEY = 'peluq.demo.v2';
  const ADMIN_PIN = '1234'; // PIN de administrador para la demo

  // Asegura que "Prueba de Color" exista aunque se cargue un data.js viejo.
  (function ensureExtra() {
    const d = window.DEMO_DATA;
    if (d && !d.servicios.some(s => s.nombre.toUpperCase().trim() === 'PRUEBA DE COLOR')) {
      d.servicios.push({ nombre: 'PRUEBA DE COLOR', precio_usd: 5, area: 'peluqueria' });
    }
  })();

  function todayKey() {
    const dt = new Date();
    return `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, '0')}-${String(dt.getDate()).padStart(2, '0')}`;
  }

  function defaultState() {
    const data = window.DEMO_DATA || { staff: [], servicios: [], areas: [] };
    const areaKeys = data.areas.map(a => a.key);

    const staff = data.staff.map((s, i) => {
      // Área principal por rango de número (heurística de la demo).
      let primary = 'peluqueria';
      if (s.numero >= 56 && s.numero <= 76) primary = 'hidratacion';
      else if (s.numero >= 77) primary = 'manicure';
      if ([4, 12, 18, 25, 33].includes(s.numero)) primary = 'cejas';

      const areas = [primary];
      // ~1/3 del personal maneja una segunda área.
      if (s.numero % 3 === 0) {
        const alt = areaKeys[(areaKeys.indexOf(primary) + 1) % areaKeys.length];
        if (alt && alt !== primary) areas.push(alt);
      }
      return {
        ...s,
        areas,
        manualStatus: (i % 7 === 0) ? 'BREAK' : 'DISPONIBLE',
        en_prueba: (s.numero % 19 === 0), // algunas marcadas "En prueba"
      };
    });

    return {
      day: todayKey(),
      turn_seq: 12,
      clientes: [],
      staff,
      historial: seedHistorial(staff, data),
    };
  }

  // Un puñado de servicios finalizados de ejemplo para que el historial
  // no arranque vacío en la demo.
  function seedHistorial(staff, data) {
    const now = Date.now();
    const pick = n => staff.find(s => s.numero === n) || staff[0];
    const svc = name => data.servicios.find(s => s.nombre.toUpperCase().includes(name)) || data.servicios[0];
    const rows = [
      { min: 210, cli: 'Rosa Delgado', ci: 'V-14.220.100', st: 2, sv: 'CORTE DAMA' },
      { min: 180, cli: 'Rosa Delgado', ci: 'V-14.220.100', st: 3, sv: 'HIDRATACION SALERM' },
      { min: 150, cli: 'Andrea Ruiz', ci: 'V-27.550.019', st: 5, sv: 'MANICURE SEMI' },
      { min: 95, cli: 'Luisa Marín', ci: 'V-19.880.442', st: 2, sv: 'SECADO DOMINICANO' },
      { min: 40, cli: 'Andrea Ruiz', ci: 'V-27.550.019', st: 8, sv: 'DISEÑO Y DEPILACION DE CEJAS' },
    ];
    return rows.map((r, i) => {
      const st = pick(r.st); const s = svc(r.sv);
      return {
        id: `h_seed_${i}`,
        ts: now - r.min * 60000,
        cliente_id: `seed_${r.ci}`,
        cliente_nombre: r.cli,
        cliente_cedula: r.ci,
        servicio_nombre: s.nombre,
        area: s.area,
        precio_usd: s.precio_usd,
        staff_id: st.numero,
        staff_nombre: st.alias,
        cambios: [],
      };
    });
  }

  function turnEstado(c) {
    const sv = c.servicios;
    if (sv.length && sv.every(x => x.estado === 'FINALIZADO')) return 'FINALIZADO';
    if (sv.some(x => x.estado !== 'PENDIENTE')) return 'EN_ATENCION';
    return 'EN_ESPERA';
  }

  // Añade campos derivados (estado efectivo del personal, estado del turno).
  function withDerived(s) {
    const active = {};
    s.clientes.forEach(c =>
      c.servicios.forEach(sv => {
        if (sv.estado === 'EN_ATENCION' && sv.staff_id != null) {
          (active[sv.staff_id] = active[sv.staff_id] || []).push({ turno: c.turno, cliente: c.nombre, servicio: sv.nombre });
        }
      })
    );
    s.staff.forEach(st => {
      st.activos = active[st.numero] || [];
      st.busy = st.activos.length > 0;
      st.status = st.busy ? 'OCUPADO' : st.manualStatus; // efectivo
    });
    s.clientes.forEach(c => { c.estado = turnEstado(c); });
    return s;
  }

  function loadRaw() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultState();
      const s = JSON.parse(raw);
      if (s.day !== todayKey()) return defaultState();
      if (!s.staff || s.staff.length !== (window.DEMO_DATA?.staff?.length || 0)) {
        const fresh = defaultState();
        fresh.clientes = s.clientes || [];
        fresh.turn_seq = s.turn_seq || 12;
        fresh.historial = s.historial || fresh.historial;
        return fresh;
      }
      s.historial = s.historial || [];
      return s;
    } catch (e) {
      return defaultState();
    }
  }

  function save(s) {
    localStorage.setItem(KEY, JSON.stringify(s));
    window.dispatchEvent(new CustomEvent('peluq:change'));
  }

  function findStaff(s, numero) { return s.staff.find(x => x.numero === Number(numero)); }

  const Store = {
    ADMIN_PIN_HINT: '1234',

    get() { return withDerived(loadRaw()); },

    reset() { localStorage.removeItem(KEY); window.dispatchEvent(new CustomEvent('peluq:change')); },

    validatePin(pin) { return String(pin).trim() === ADMIN_PIN; },

    turnEstado,

    // Personal cuyas áreas cubren `area` y que está DISPONIBLE.
    eligibleStaff(area) {
      const s = this.get();
      return s.staff.filter(st => st.areas.includes(area) && st.status === 'DISPONIBLE');
    },

    addCliente(payload) {
      const s = loadRaw();
      s.turn_seq += 1;
      const servicios = (payload.servicios || []).map((sv, idx) => ({
        id: `sv_${Date.now()}_${idx}`,
        area: sv.area,
        nombre: sv.nombre,
        precio_usd: sv.precio_usd,
        staff_id: null,
        estado: 'PENDIENTE',
        cambios: [],
      }));
      const cliente = {
        id: `c_${Date.now()}`,
        ts: Date.now(),
        turno: s.turn_seq,
        cedula: payload.cedula,
        nombre: payload.nombre,
        telefono: payload.telefono,
        direccion: payload.direccion,
        observacion: payload.observacion || '',
        estado: 'EN_ESPERA',
        servicios,
      };
      s.clientes.push(cliente);
      save(s);
      return cliente;
    },

    assignService(clienteId, servicioId, staffId) {
      const s = loadRaw();
      const c = s.clientes.find(x => x.id === clienteId);
      const sv = c && c.servicios.find(x => x.id === servicioId);
      if (!sv) return;
      sv.staff_id = Number(staffId);
      sv.estado = 'EN_ATENCION';
      c.estado = turnEstado(c);
      save(s);
    },

    // Asigna varios servicios de un mismo turno al mismo especialista.
    assignMany(clienteId, servicioIds, staffId) {
      const s = loadRaw();
      const c = s.clientes.find(x => x.id === clienteId);
      if (!c) return;
      servicioIds.forEach(id => {
        const sv = c.servicios.find(x => x.id === id);
        if (sv) { sv.staff_id = Number(staffId); sv.estado = 'EN_ATENCION'; }
      });
      c.estado = turnEstado(c);
      save(s);
    },

    finishService(clienteId, servicioId) {
      const s = loadRaw();
      const c = s.clientes.find(x => x.id === clienteId);
      const sv = c && c.servicios.find(x => x.id === servicioId);
      if (!sv) return;
      sv.estado = 'FINALIZADO';
      const st = findStaff(s, sv.staff_id);
      s.historial.push({
        id: `h_${Date.now()}_${sv.id}`,
        ts: Date.now(),
        cliente_id: c.id,
        cliente_nombre: c.nombre,
        cliente_cedula: c.cedula,
        servicio_nombre: sv.nombre,
        area: sv.area,
        precio_usd: sv.precio_usd,
        staff_id: sv.staff_id,
        staff_nombre: st ? st.alias : '—',
        cambios: sv.cambios.slice(),
      });
      c.estado = turnEstado(c);
      save(s);
    },

    // Requiere PIN de admin. Devuelve {ok, error?}.
    changeSpecialist(clienteId, servicioId, newStaffId, pin, motivo) {
      if (!this.validatePin(pin)) return { ok: false, error: 'PIN de administrador inválido.' };
      if (!motivo || !motivo.trim()) return { ok: false, error: 'El motivo del cambio es obligatorio.' };
      const s = loadRaw();
      const c = s.clientes.find(x => x.id === clienteId);
      const sv = c && c.servicios.find(x => x.id === servicioId);
      if (!sv) return { ok: false, error: 'Servicio no encontrado.' };
      sv.cambios.push({ ts: Date.now(), de: sv.staff_id, a: Number(newStaffId), motivo: motivo.trim() });
      sv.staff_id = Number(newStaffId);
      sv.estado = 'EN_ATENCION';
      c.estado = turnEstado(c);
      save(s);
      return { ok: true };
    },

    setStaffManualStatus(numero, status) {
      const s = loadRaw();
      const st = findStaff(s, numero);
      if (!st) return;
      st.manualStatus = status; // DISPONIBLE | BREAK
      save(s);
    },

    toggleEnPrueba(numero) {
      const s = loadRaw();
      const st = findStaff(s, numero);
      if (!st) return;
      st.en_prueba = !st.en_prueba;
      save(s);
    },

    onChange(cb) {
      window.addEventListener('peluq:change', () => cb(this.get()));
      window.addEventListener('storage', e => { if (e.key === KEY) cb(this.get()); });
    },
  };

  window.PeluqStore = Store;
})();
