(() => {
  frappe.pages['wise-setup'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({parent: wrapper, title: __('Wise Bank Feed'), single_column: true});
    const content = $('<div class="wise-setup"></div>').appendTo(page.main);
    $(`<style>
      .wise-setup {max-width: 960px; margin: 0 auto; padding: 32px 24px 48px;}
      .wise-setup .wise-brand {display: block; width: 360px; max-width: 100%; height: auto; margin-bottom: 28px;}
      .wise-setup .wise-eyebrow {color: var(--text-muted); font-size: 12px; margin-bottom: 8px;}
      .wise-setup h2 {font-size: 28px; line-height: 1.2; margin-bottom: 12px;}
      .wise-setup .wise-intro {color: var(--text-muted); max-width: 600px; margin-bottom: 24px;}
      .wise-setup .wise-actions {display: flex; flex-wrap: wrap; gap: 8px; margin: 16px 0 28px;}
      .wise-setup .wise-actions .btn {min-height: 36px;}
      .wise-setup .wise-primary {background: #9fe870; color: #163300; border-color: #9fe870; font-weight: 600;}
      .wise-setup .wise-primary:hover {background: #b7ef92; border-color: #b7ef92; color: #163300;}
      .wise-setup .wise-note {padding: 18px 20px; background: var(--control-bg); border: 1px solid var(--border-color); border-radius: 12px; margin-bottom: 28px;}
      .wise-setup .wise-note p {margin: 6px 0 0; color: var(--text-muted);}
      .wise-setup .wise-steps {list-style: none; padding: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; counter-reset: wise-step;}
      .wise-setup .wise-steps li {padding: 20px; border: 1px solid var(--border-color); border-radius: 12px; counter-increment: wise-step;}
      .wise-setup .wise-steps li::before {content: counter(wise-step); display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: var(--control-bg); font-size: 12px; font-weight: 600; margin-bottom: 18px;}
      .wise-setup .wise-steps h3 {font-size: 15px; margin: 0 0 8px;}
      .wise-setup .wise-steps p {color: var(--text-muted); margin: 0; font-size: 13px; line-height: 1.6;}
      .wise-setup .wise-tools-title {font-size: 15px; margin-top: 32px;}
      .wise-setup .wise-footer {font-size: 12px; color: var(--text-muted);}
      @media (max-width: 640px) {.wise-setup {padding: 24px 16px;} .wise-setup .wise-steps {grid-template-columns: 1fr;} .wise-setup h2 {font-size: 24px;}}
    </style>`).appendTo(content);
    $('<img class="wise-brand" width="480" height="96" alt="ERPNext ↔ Wise" src="/assets/wise_bank_feed/images/integration.svg">').appendTo(content);
    $('<p class="wise-eyebrow"></p>').text(__('UNOFFICIAL INTEGRATION · READ-ONLY')).appendTo(content);
    $('<h2></h2>').text(__('Your Wise activity, ready to review')).appendTo(content);
    $('<p class="wise-intro"></p>').text(__('Connect your business, choose the accounts you need, and review activity in ERPNext. Your API token stays encrypted on this server.')).appendTo(content);
    function button(container, label, action, primary = false) {
      $('<button type="button" class="btn"></button>').addClass(primary ? 'wise-primary' : 'btn-default').text(__(label)).on('click', action).appendTo(container);
    }
    const actions = $('<div class="wise-actions"></div>').appendTo(content);
    button(actions, 'New connection', () => frappe.new_doc('Wise Connection', {mode: 'Activity Review', environment: 'Production', timezone: 'Europe/London', start_date: frappe.datetime.add_days(frappe.datetime.get_today(), -30)}), true);
    button(actions, 'Activity inbox', () => frappe.set_route('List', 'Wise Activity', {needs_review: 1}));
    button(actions, 'Connections', () => frappe.set_route('List', 'Wise Connection'));
    const note = $('<div class="wise-note"></div>').appendTo(content);
    $('<strong></strong>').text(__('Activity review or automatic statements?')).appendTo(note);
    $('<p></p>').text(__('Activity Review collects summaries every 15 minutes. Verify booked amounts, fees and dates in Wise before creating bank entries. Automatic imports need statement API access; a personal token may not provide it.')).appendTo(note);
    const steps = $('<ol class="wise-steps"></ol>').appendTo(content);
    [
      [__('Connect your business'), __('Create a connection with your company, read-only Wise token and start date. Save, then Discover profiles and choose your business.')],
      [__('Choose your accounts'), __('Discover accounts, then map the ones you want to ERPNext Bank Accounts. Leave any unfamiliar accounts unmapped.')],
      [__('Start reviewing'), __('Enable the connection and select Sync Now. Open the activity inbox to check booked details and create bank entries.')]
    ].forEach(([title, description]) => {
      const step = $('<li></li>').appendTo(steps);
      $('<h3></h3>').text(title).appendTo(step);
      $('<p></p>').text(description).appendTo(step);
    });
    $('<h3 class="wise-tools-title"></h3>').text(__('Manage your feed')).appendTo(content);
    const tools = $('<div class="wise-actions"></div>').appendTo(content);
    button(tools, 'Account mappings', () => frappe.set_route('List', 'Wise Account Map'));
    button(tools, 'Source reviews', () => frappe.set_route('List', 'Wise Booking', {needs_review: 1}));
    button(tools, 'Sync logs', () => frappe.set_route('List', 'Wise Sync Log'));
    button(tools, 'Create ERPNext Bank Account', () => frappe.new_doc('Bank Account', {is_company_account: 1}));
    $('<p class="wise-footer"></p>').text(__('Pause a connection before changing its mappings. Keep your site encryption key with your backups.')).appendTo(content);
  };
})();
