(() => {
  frappe.pages['wise-setup'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Connect Wise'), single_column: true});
    const root = $('<div class="wise-wizard"></div>').appendTo(page.main);
    const esc = frappe.utils.escape_html;
    let current = null, accounts = [], profiles = [], saved = [], step = 0, busy = false;
    const steps = ['Connect', 'Business', 'Accounts', 'Sync'];
    $('<style>').text(`
      .wise-wizard{max-width:920px;margin:0 auto;padding:30px 20px 60px}
      .wise-wizard .wise-brand{width:340px;max-width:85%;height:auto;margin-bottom:28px}
      .wise-wizard h2{font-size:27px;letter-spacing:-.5px;margin:0 0 10px}
      .wise-wizard .muted{color:var(--text-muted);line-height:1.6}
      .wise-wizard .wise-steps{display:flex;padding:0;list-style:none;margin:30px 0;gap:10px}
      .wise-wizard .wise-steps li{flex:1;border-top:3px solid var(--border-color);padding-top:10px;font-size:13px;color:var(--text-muted)}
      .wise-wizard .wise-steps li.active{border-color:#78b84c;color:var(--text-color);font-weight:600}
      .wise-wizard .wise-card{background:var(--card-bg);border:1px solid var(--border-color);border-radius:16px;padding:28px}
      .wise-wizard .wise-fields{max-width:560px;margin-top:22px}
      .wise-wizard .wise-actions{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:24px}
      .wise-wizard .wise-primary{background:#9fe870;border-color:#9fe870;color:#163300;font-weight:600}
      .wise-wizard .btn{min-height:38px;padding:8px 16px}
      .wise-wizard .wise-error{color:var(--red-600);background:var(--red-50);padding:12px 16px;border-radius:8px;margin-bottom:16px}
      .wise-wizard .wise-profile{display:flex;align-items:center;gap:14px;padding:18px;border:1px solid var(--border-color);border-radius:10px;margin-top:12px;cursor:pointer}
      .wise-wizard .wise-profile:has(input:checked){border-color:#78b84c;background:var(--control-bg)}
      .wise-wizard .wise-account{display:grid;grid-template-columns:1fr 1fr;gap:20px;padding:20px 0;border-bottom:1px solid var(--border-color)}
      .wise-wizard .wise-account:last-child{border-bottom:0}
      .wise-wizard .wise-account strong{display:block;margin-bottom:5px}
      .wise-wizard .wise-account .frappe-control{margin-bottom:0}
      .wise-wizard .wise-summary{padding:16px 0;border-bottom:1px solid var(--border-color)}
      .wise-wizard .wise-tools{display:flex;gap:18px;flex-wrap:wrap;margin-top:24px;font-size:13px}
      .wise-wizard .wise-resume{margin-top:20px;max-width:560px}
      .wise-wizard .wise-success{display:inline-block;background:#9fe870;color:#163300;border-radius:20px;padding:5px 12px;margin-bottom:15px;font-weight:600;font-size:12px}
      @media(max-width:600px){.wise-wizard{padding:20px 12px}.wise-wizard .wise-card{padding:20px}.wise-wizard .wise-account{grid-template-columns:1fr;gap:12px}.wise-wizard .wise-steps{gap:6px}}
    `).appendTo(page.main);
    const call = async (method, args = {}) => (await frappe.call({method: `wise_bank_feed.setup.${method}`, args})).message;
    function apply(data) { current = data.connection; accounts = data.accounts || []; }
    async function action(fn) {
      if (busy) return;
      busy = true;
      root.find('.wise-error').remove();
      root.attr('aria-busy', 'true').find('button').prop('disabled', true);
      try { await fn(); }
      catch (error) {
        const message = error.message && error.message !== 'undefined' ? error.message : __('That step did not finish. Check the message from ERPNext and try again.');
        $('<div class="wise-error" role="alert"></div>').text(message).prependTo(root.find('.wise-card'));
      } finally { busy = false; root.attr('aria-busy', 'false').find('button').prop('disabled', false); }
    }
    function button(parent, label, fn, primary = false) {
      return $('<button type="button" class="btn"></button>').addClass(primary ? 'wise-primary' : 'btn-default').text(__(label)).on('click', () => action(fn)).appendTo(parent);
    }
    function field(parent, df) {
      const control = frappe.ui.form.make_control({parent, df, render_input: true});
      if (df.default !== undefined) control.set_value(df.default);
      return control;
    }
    function heading(card, title, detail) {
      $('<h2>').text(__(title)).appendTo(card);
      $('<p class="muted">').text(__(detail)).appendTo(card);
    }
    function tools() {
      const links = $('<div class="wise-tools">').appendTo(root);
      [['Activity inbox', 'Wise Activity'], ['Connections', 'Wise Connection'], ['Sync logs', 'Wise Sync Log']].forEach(([label, dt]) => {
        $('<a href="#">').text(__(label)).on('click', e => {e.preventDefault(); frappe.set_route('List', dt, current && dt !== 'Wise Connection' ? {connection: current.name} : {});}).appendTo(links);
      });
      button(links, 'New connection', async () => { current = null; accounts = []; profiles = []; render(0); });
    }
    async function resume(name) {
      apply(await call('state', {connection: name}));
      if (current.enabled) render(3);
      else if (accounts.length) render(2);
      else { profiles = await call('profiles', {connection: name}); render(1); }
    }
    function render(next) {
      step = next;
      root.empty();
      $('<img class="wise-brand" width="480" height="96" alt="ERPNext and Wise" src="/assets/wise_bank_feed/images/integration.svg">').appendTo(root);
      $('<p class="muted">').text(current ? `${current.company} · ${current.environment}${current.profile_id ? ' · Profile ' + current.profile_id : ''}` : __('WISE BANK FEED · UNOFFICIAL INTEGRATION')).appendTo(root);
      const progress = $('<ol class="wise-steps" aria-label="Setup progress">').appendTo(root);
      steps.forEach((label, i) => $('<li>').toggleClass('active', i <= step).attr('aria-current', i === step ? 'step' : null).text(`${i + 1}. ${__(label)}`).appendTo(progress));
      const card = $('<section class="wise-card">').appendTo(root);
      if (step === 0) connectView(card);
      if (step === 1) profileView(card);
      if (step === 2) accountsView(card);
      if (step === 3) syncView(card);
      tools();
    }
    function connectView(card) {
      heading(card, 'Bring Wise into your books', 'Connect your business, choose your accounts, and review transactions in ERPNext.');
      const form = $('<div class="wise-fields">').appendTo(card);
      const company = field(form, {fieldname:'company',fieldtype:'Link',options:'Company',label:__('ERPNext company'),reqd:1,default:frappe.defaults.get_user_default('Company')});
      const token = field(form, {fieldname:'token',fieldtype:'Password',label:__('Wise API token'),reqd:1,description:__('Use a read-only token from Wise Business → Settings → API tokens. Stored encrypted on this server.')});
      const date = field(form, {fieldname:'start_date',fieldtype:'Date',label:__('Import activity from'),reqd:1,default:frappe.datetime.add_days(frappe.datetime.get_today(), -30)});
      const advanced = $('<details><summary>Connection options</summary></details>').appendTo(form);
      const zone = field(advanced, {fieldname:'timezone',fieldtype:'Data',label:__('Timezone'),default:frappe.sys_defaults.time_zone || 'Europe/London',reqd:1});
      const environment = field(advanced, {fieldname:'environment',fieldtype:'Select',label:__('Environment'),options:'Production\nSandbox',default:'Production'});
      const actions = $('<div class="wise-actions">').appendTo(card);
      button(actions, 'Connect and find my business', async () => {
        if (!company.get_value() || !token.get_value() || !date.get_value() || !zone.get_value()) throw new Error(__('Enter your company, token, start date and timezone.'));
        const result = await call('connect', {company:company.get_value(),token:token.get_value(),start_date:date.get_value(),timezone:zone.get_value(),environment:environment.get_value()});
        token.set_value('');
        profiles = result.profiles;
        apply(await call('state', {connection:result.connection}));
        render(1);
      }, true);
      if (saved.length) {
        const box = $('<div class="wise-resume">').appendTo(card);
        const select = field(box, {fieldname:'resume',fieldtype:'Select',label:__('Or continue an existing connection'),options:[{label:__('Choose a connection'),value:''}, ...saved.map(c => ({label:`${c.connection_name} · ${c.profile_id || __('Not finished')}`,value:c.name}))]});
        button(box, 'Continue setup', async () => { if (select.get_value()) await resume(select.get_value()); });
      }
    }
    function profileView(card) {
      heading(card, 'Choose your Wise business', 'These business profiles are available to your token. Match the profile ID if you have more than one.');
      let selected = current.profile_id || (profiles.length === 1 ? profiles[0].id : '');
      profiles.forEach(profile => {
        const label = $('<label class="wise-profile">').appendTo(card);
        $('<input type="radio" name="wise-profile">').val(profile.id).prop('checked', selected === profile.id).on('change', () => {selected = profile.id;}).appendTo(label);
        const text = $('<span>').appendTo(label);
        $('<strong>').text(profile.label).appendTo(text);
        $('<div class="muted">').text(`Profile ID: ${profile.id}`).appendTo(text);
      });
      if (!profiles.length) $('<p>').text(__('No business profiles found. Check that your token belongs to Wise Business.')).appendTo(card);
      const actions = $('<div class="wise-actions">').appendTo(card);
      button(actions, 'Find my accounts', async () => {
        if (!selected) throw new Error(__('Choose a business profile.'));
        apply(await call('select_profile', {connection:current.name,profile_id:selected})); render(2);
      }, true);
      button(actions, 'Refresh profiles', async () => {profiles = await call('profiles', {connection:current.name}); render(1);});
    }
    function accountsView(card) {
      heading(card, 'Choose the accounts you want', 'Link each Wise balance to an ERPNext Bank Account in the same currency. Leave any account blank to skip it.');
      const controls = [];
      accounts.forEach(account => {
        const row = $('<div class="wise-account">').appendTo(card);
        const info = $('<div>').appendTo(row);
        $('<strong>').text(`${account.currency} · ${account.account_name || __('Wise balance')}`).appendTo(info);
        $('<div class="muted">').text(`Balance ID: ${account.balance_id} · ${account.balance_type || ''}`).appendTo(info);
        $('<div class="muted">').text(account.available ? `${__('Reported balance')}: ${account.reported_balance || '0'} ${account.currency}` : __('No longer available — skip this account.')).appendTo(info);
        const target = $('<div>').appendTo(row);
        const control = field(target, {fieldname:`map_${account.name}`,fieldtype:'Link',options:'Bank Account',label:__('ERPNext Bank Account') + ` (${account.currency})`,default:account.bank_account || '',read_only:!account.available,description:__('Blank = skipped')});
        control.get_query = () => ({filters:{company:current.company,is_company_account:1}});
        controls.push({name:account.name,control,available:account.available});
      });
      if (!accounts.length) $('<p>').text(__('No balances found yet. Refresh accounts after adding a balance in Wise.')).appendTo(card);
      const actions = $('<div class="wise-actions">').appendTo(card);
      button(actions, 'Save accounts and continue', async () => {
        apply(await call('save_mappings', {connection:current.name,mappings:JSON.stringify(controls.map(row => ({name:row.name,bank_account:row.available ? row.control.get_value() || '' : ''})))})); render(3);
      }, true);
      button(actions, 'Refresh accounts', async () => {
        await frappe.call({method:'wise_bank_feed.api.discover_accounts',args:{connection:current.name}});
        apply(await call('state', {connection:current.name})); render(2);
      });
      button(actions, 'Create ERPNext Bank Account', async () => {frappe.new_doc('Bank Account', {company:current.company,is_company_account:1});});
    }
    function syncView(card) {
      const mapped = accounts.filter(a => a.enabled && a.available && a.bank_account);
      if (current.enabled) $('<span class="wise-success">').text(__('Activity sync enabled')).appendTo(card);
      heading(card, current.enabled ? 'Your Wise feed is connected' : 'Ready for your first sync', 'Activity syncs every 15 minutes. Review booked details in the inbox to create Bank Transactions for reconciliation.');
      $('<p class="muted">').text(`${mapped.length} ${__('accounts selected')} · ${__('History from')} ${current.start_date}`).appendTo(card);
      mapped.forEach(a => $('<div class="wise-summary">').html(`<strong>${esc(a.currency)} · ${esc(a.account_name || '')}</strong><br><span class="muted">${esc(a.bank_account)}</span>`).appendTo(card));
      if (!mapped.length) $('<p>').text(__('Go back and map at least one account to start syncing.')).appendTo(card);
      if (current.last_success) $('<p class="muted">').text(`${__('Last successful sync')}: ${current.last_success}`).appendTo(card);
      if (current.status) $('<p class="muted">').text(current.status).appendTo(card);
      const actions = $('<div class="wise-actions">').appendTo(card);
      button(actions, current.enabled ? 'Sync now' : 'Start activity sync', async () => {
        apply(await call('start', {connection:current.name})); render(3); frappe.show_alert({message:__('Sync queued. Transactions will appear in the activity inbox.'),indicator:'green'});
      }, true);
      if (current.enabled) button(actions, 'Open activity inbox', async () => {frappe.set_route('List','Wise Activity',{connection:current.name});});
      button(actions, current.enabled ? 'Pause and edit accounts' : 'Back to accounts', async () => {
        if (current.enabled) apply(await call('pause', {connection:current.name})); render(2);
      });
      button(actions, 'Refresh status', async () => {apply(await call('state', {connection:current.name})); render(3);});
    }
    render(0);
    action(async () => {
      saved = await call('connections');
      if (saved.length === 1) await resume(saved[0].name);
      else render(0);
    });
  };
})();
