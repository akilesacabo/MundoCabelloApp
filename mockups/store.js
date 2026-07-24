// Mini "backend" en memoria + localStorage para la demo.
// Permite que el flujo (check-in -> confirmacion -> panel -> staff)
// comparta estado entre pestañas/recargas durante la presentacion.
(function () {
  const KEY = 'peluq.demo.v1';

  function todayKey() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  function defaultState() {
    const data = window.DEMO_DATA || { staff: [], servicios: [], areas: [] };
    // Estados iniciales del personal: ~70% Disponible, ~20% Ocupado, ~10% Break
    const statuses = ['DISPONIBLE', 'DISPONIBLE', 'DISPONIBLE', 'DISPONIBLE', 'DISPONIBLE', 'DISPONIBLE', 'DISPONIBLE', 'OCUPADO', 'OCUPADO', 'BREAK'];
    const staff = data.staff.map((s, i) => {
      const u = s.nombre.toUpperCase();
      let area = 'peluqueria';
      if (s.numero >= 56 && s.numero <= 76) area = 'hidratacion';
      else if (s.numero >= 77) area = 'manicure';
      // pequeña inyección para que cejas tenga gente
      if ([4, 12, 18, 25, 33].includes(s.numero)) area = 'cejas';
      return {
        ...s,
        area,
        status: statuses[(i + s.numero) % statuses.length],
        cliente_id: null,
      };
    });
    return {
      day: todayKey(),
      turn_seq: 12,
      clientes: [],   // {id, cedula, nombre, telefono, direccion, servicios:[{area, nombre, precio_usd}], turno, estado, staff_id, ts}
      staff,
    };
  }

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultState();
      const s = JSON.parse(raw);
      if (s.day !== todayKey()) return defaultState(); // reset diario
      // Si cambió el dataset, re-seed staff
      if (!s.staff || s.staff.length !== (window.DEMO_DATA?.staff?.length || 0)) {
        const fresh = defaultState();
        fresh.clientes = s.clientes || [];
        fresh.turn_seq = s.turn_seq || 12;
        return fresh;
      }
      return s;
    } catch (e) {
      return defaultState();
    }
  }

  function save(s) {
    localStorage.setItem(KEY, JSON.stringify(s));
    // notificar a otras pestañas/pantallas
    window.dispatchEvent(new CustomEvent('peluq:change', { detail: s }));
  }

  const Store = {
    get() { return load(); },
    reset() { localStorage.removeItem(KEY); window.dispatchEvent(new CustomEvent('peluq:change', { detail: load() })); },
    addCliente(payload) {
      const s = load();
      s.turn_seq += 1;
      const cliente = {
        id: `c_${Date.now()}`,
        ts: Date.now(),
        estado: 'EN_ESPERA',
        staff_id: null,
        turno: s.turn_seq,
        ...payload,
      };
      s.clientes.push(cliente);
      save(s);
      return cliente;
    },
    assign(clienteId, staffId) {
      const s = load();
      const c = s.clientes.find(x => x.id === clienteId);
      const st = s.staff.find(x => x.numero === staffId);
      if (!c || !st) return null;
      c.estado = 'EN_ATENCION';
      c.staff_id = staffId;
      st.status = 'OCUPADO';
      st.cliente_id = clienteId;
      save(s);
      return c;
    },
    finish(clienteId) {
      const s = load();
      const c = s.clientes.find(x => x.id === clienteId);
      if (!c) return null;
      c.estado = 'FINALIZADO';
      const st = s.staff.find(x => x.numero === c.staff_id);
      if (st) { st.status = 'DISPONIBLE'; st.cliente_id = null; }
      save(s);
      return c;
    },
    setStaffStatus(staffId, status) {
      const s = load();
      const st = s.staff.find(x => x.numero === staffId);
      if (!st) return;
      st.status = status;
      if (status !== 'OCUPADO') st.cliente_id = null;
      save(s);
    },
    onChange(cb) {
      window.addEventListener('peluq:change', () => cb(load()));
      window.addEventListener('storage', (e) => { if (e.key === KEY) cb(load()); });
    },
  };

  window.PeluqStore = Store;
})();
