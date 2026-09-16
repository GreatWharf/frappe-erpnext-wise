// Behavioral tests for Desk scripts, with only Frappe/DOM boundaries replaced.
// Run with: node --test tests/test_ui.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..', 'wise_bank_feed', 'wise_bank_feed');
const scripts = {
  connection: fs.readFileSync(path.join(root, 'doctype/wise_connection/wise_connection.js'), 'utf8'),
  setup: fs.readFileSync(path.join(root, 'page/wise_setup/wise_setup.js'), 'utf8'),
};
const plain = value => JSON.parse(JSON.stringify(value));

function connectionForm({enabled = 0, dirty = false, isNew = false, mode = 'Activity Review'} = {}) {
  const buttons = [], calls = [], routes = [], messages = [], primary = [];
  let handlers;
  const frappe = {
    ui: {form: {on: (doctype, value) => { handlers = value; }}},
    set_route: (...route) => routes.push(route),
    msgprint: message => messages.push(message),
    show_alert: message => messages.push(message),
    call: async options => { calls.push(options); return {message: []}; },
  };
  const frm = {
    doc: {name: 'conn-2', enabled, mode, profile_id: '123'},
    is_new: () => isNew,
    is_dirty: () => dirty,
    add_custom_button: (label, run, group) => { buttons.push({label, run, group}); return {prop() {return this;}}; },
    change_custom_button_type: (label, group, type) => { if (type === 'primary') primary.push(label); },
    dashboard: {set_headline_alert() {}},
  };
  vm.runInNewContext(scripts.connection, {frappe, __: value => value});
  handlers.refresh(frm);
  return {frappe, frm, buttons, calls, routes, messages, primary};
}

test('enabled connection has one primary Sync Now and grouped Setup/View actions', () => {
  const form = connectionForm({enabled: 1});
  assert.deepEqual(form.primary, ['Sync Now']);
  assert.ok(form.buttons.some(button => button.group === 'Setup'));
  assert.ok(form.buttons.some(button => button.label === 'Activity inbox' && button.group === 'View'));
  assert.ok(form.buttons.some(button => button.label === 'Sync logs' && button.group === 'View'));
  assert.deepEqual(form.buttons.filter(button => !button.group).map(button => button.label), ['Sync Now']);
  assert.ok(!form.buttons.some(button => button.label.startsWith('Discover')));
});

test('paused connection continues setup for its own connection', async () => {
  const form = connectionForm();
  assert.deepEqual(form.primary, ['Continue setup']);
  await form.buttons.find(button => button.label === 'Continue setup').run();
  assert.deepEqual(plain(form.frappe.route_options), {connection: 'conn-2'});
  assert.deepEqual(form.routes, [['wise-setup']]);
  assert.ok(form.buttons.filter(button => button.label.startsWith('Discover')).every(button => button.group === 'Setup'));
  assert.ok(!form.buttons.some(button => button.label === 'Sync Now'));
});

test('dirty connection does not queue a sync or navigate away', async () => {
  const active = connectionForm({enabled: 1, dirty: true});
  await active.buttons.find(button => button.label === 'Sync Now').run();
  assert.equal(active.calls.length, 0);
  assert.ok(active.messages.some(message => /save/i.test(message)));
  const paused = connectionForm({dirty: true});
  const setup = paused.buttons.find(button => button.label === 'Continue setup');
  assert.ok(setup, 'A saved paused connection offers Continue setup');
  await setup.run();
  assert.equal(paused.routes.length, 0);
});

test('repeated Sync Now clicks enqueue only once while the call is pending', async () => {
  const form = connectionForm({enabled: 1});
  let finish;
  form.frappe.call = options => {
    form.calls.push(options);
    return new Promise(resolve => { finish = resolve; });
  };
  const sync = form.buttons.find(button => button.label === 'Sync Now');
  const first = sync.run();
  const second = sync.run();
  assert.equal(form.calls.length, 1);
  finish({message: 'Queued'});
  await Promise.all([first, second]);
  assert.equal(form.calls[0].freeze, true);
});

test('new connection opens a new wizard without replacing the native Save action', async () => {
  const form = connectionForm({isNew: true});
  await form.buttons.find(button => button.label === 'Guided setup').run();
  assert.ok(form.frappe.route_options, 'New setup navigation must not resume a saved connection');
  assert.deepEqual(plain(form.frappe.route_options), {new_connection: 1});
  assert.deepEqual(form.primary, []);
});

test('statements connection offers booking records instead of activity inbox', () => {
  const form = connectionForm({enabled: 1, mode: 'Statements'});
  assert.ok(form.buttons.some(button => button.label === 'Booking records' && button.group === 'View'));
  assert.ok(!form.buttons.some(button => button.label === 'Activity inbox'));
});

// Minimal jQuery surface for testing callbacks and emitted controls, not layout/rendering.
function dom() {
  class Element {
    constructor(markup = '') {
      this.markup = markup; this.children = []; this.events = {}; this.props = {};
      this.classes = new Set((markup.match(/class="([^"]*)"/)?.[1] || '').split(' '));
      this.tag = markup.match(/^<(\w+)/)?.[1]; this.value = ''; this.textValue = '';
    }
    appendTo(parent) { this.parent = parent; parent.children.push(this); return this; }
    prependTo(parent) { return this.appendTo(parent instanceof Collection ? parent.items[0] : parent); }
    text(value) { this.textValue = value; return this; }
    html(value) { this.textValue = value; return this; }
    addClass(value) { this.classes.add(value); return this; }
    toggleClass(value, enabled) { if (enabled) this.classes.add(value); else this.classes.delete(value); return this; }
    on(event, handler) { this.events[event] = handler; return this; }
    attr(name, value) { this.props[name] = value; return this; }
    prop(name, value) { this.props[name] = value; return this; }
    val(value) { if (value === undefined) return this.value; this.value = value; return this; }
    empty() { this.children = []; return this; }
    remove() { if (this.parent) this.parent.children = this.parent.children.filter(item => item !== this); return this; }
    find(selector) { return new Collection(descendants(this).filter(item => selector.startsWith('.') ? item.classes.has(selector.slice(1)) : item.tag === selector)); }
  }
  class Collection {
    constructor(items) { this.items = items; }
    prop(name, value) { this.items.forEach(item => item.prop(name, value)); return this; }
    remove() { this.items.forEach(item => item.remove()); return this; }
  }
  function descendants(element) { return element.children.flatMap(child => [child, ...descendants(child)]); }
  return {Element, descendants, $: markup => markup instanceof Element ? markup : new Element(markup)};
}

async function wizard({enabled = 0, mode = 'Activity Review', available = 1, selected = 1, multiple = false, routeOptions} = {}) {
  const {Element, descendants, $} = dom();
  const main = new Element(), controls = [], calls = [], routes = [], alerts = [];
  const state = {
    connection: {name: 'conn-2', company: 'Company A', environment: 'Production', profile_id: '123', enabled, mode, start_date: '2026-09-01'},
    accounts: [{name: 'map', currency: 'GBP', available, bank_account: 'bank', enabled: selected}],
  };
  const frappe = {
    pages: {'wise-setup': {}}, route_options: routeOptions,
    ui: {
      make_app_page: () => ({main}),
      form: {make_control: ({df}) => {
        const control = {df, value: '', set_value(value) {this.value = value;}, get_value() {return this.value;}};
        controls.push(control); return control;
      }},
    },
    utils: {escape_html: value => String(value)},
    defaults: {get_user_default: () => 'Company A'},
    datetime: {get_today: () => '2026-09-16', add_days: () => '2026-08-17'},
    sys_defaults: {time_zone: 'Europe/London'},
    set_route: (...route) => routes.push(route),
    show_alert: message => alerts.push(message),
    call: async options => {
      calls.push(options);
      const method = options.method.split('.').pop();
      if (method === 'connections') return {message: multiple ? [state.connection, {name: 'other'}] : [state.connection]};
      if (method === 'profiles') return {message: [{id: '123', label: 'Company A'}]};
      if (method === 'start') state.connection.enabled = 1;
      return {message: structuredClone(state)};
    },
  };
  vm.runInNewContext(scripts.setup, {frappe, $, __: value => value});
  const wrapper = {};
  frappe.pages['wise-setup'].on_page_load(wrapper);
  if (frappe.pages['wise-setup'].on_page_show) await frappe.pages['wise-setup'].on_page_show(wrapper);
  await new Promise(resolve => setImmediate(resolve));
  const elements = () => descendants(main);
  const click = async label => {
    const button = elements().find(item => item.tag === 'button' && item.textValue === label);
    assert.ok(button, `Missing button: ${label}`);
    await button.events.click();
    await new Promise(resolve => setImmediate(resolve));
  };
  return {frappe, wrapper, controls, calls, routes, alerts, state, elements, click};
}

test('wizard resumes the requested connection even with multiple saved connections', async () => {
  const view = await wizard({multiple: true, routeOptions: {connection: 'conn-2'}});
  assert.ok(view.calls.some(call => call.method.endsWith('.state') && call.args.connection === 'conn-2'));
  assert.equal(view.frappe.route_options, null);
});

test('cached wizard handles a different connection on its next page show', async () => {
  const view = await wizard();
  view.frappe.route_options = {connection: 'other'};
  assert.equal(typeof view.frappe.pages['wise-setup'].on_page_show, 'function');
  await view.frappe.pages['wise-setup'].on_page_show(view.wrapper);
  assert.ok(view.calls.some(call => call.method.endsWith('.state') && call.args.connection === 'other'));
});

test('wizard sends explicit skip without clearing the bank mapping', async () => {
  const view = await wizard();
  const selection = view.controls.find(control => control.df.fieldname === 'enabled_map');
  assert.ok(selection, 'Account inclusion is separate from bank mapping');
  selection.set_value(0);
  await view.click('Save accounts and continue');
  const saved = view.calls.find(call => call.method.endsWith('.save_mappings'));
  assert.deepEqual(JSON.parse(saved.args.mappings), [{name: 'map', bank_account: 'bank', enabled: 0}]);
});

test('unavailable wizard account retains bank identity and is sent disabled', async () => {
  const view = await wizard({available: 0});
  await view.click('Save accounts and continue');
  const saved = view.calls.find(call => call.method.endsWith('.save_mappings'));
  assert.deepEqual(JSON.parse(saved.args.mappings), [{name: 'map', bank_account: 'bank', enabled: 0}]);
});

test('statements wizard uses statement copy and a booking-record destination', async () => {
  const view = await wizard({mode: 'Statements'});
  await view.click('Save accounts and continue');
  assert.ok(view.elements().some(item => /Statements sync every 15 minutes/.test(item.textValue)));
  await view.click('Start statement sync');
  assert.ok(view.alerts.some(alert => /Bank Transactions/.test(alert.message)));
  await view.click('Open booking records');
  assert.deepEqual(plain(view.routes.at(-1)), ['List', 'Wise Booking', {connection: 'conn-2'}]);
  assert.ok(!view.elements().some(item => item.textValue === 'Activity sync enabled'));
});
