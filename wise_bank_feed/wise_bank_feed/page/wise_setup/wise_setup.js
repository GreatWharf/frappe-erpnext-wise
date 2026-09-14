(() => {
  frappe.pages['wise-setup'].on_page_load = function(wrapper) {
    const page = frappe.ui.make_app_page({parent:wrapper,title:__('Wise Bank Feed'),single_column:true});
    const content = $('<div class="p-4"></div>').appendTo(page.main);
    $('<h3></h3>').text(__('Connect your Wise Business account')).appendTo(content);
    $('<p></p>').text(__('Direct, read-only access. Your API token is encrypted in ERPNext.')).appendTo(content);
    $('<div class="alert alert-info"></div>').text(__('Activity Review automatically collects activity summaries. Confirm booked details before creating Bank Transactions. Automatic statement imports require statement API access.')).appendTo(content);
    const steps = $('<ol></ol>').appendTo(content);
    [__('Create a connection: company, read-only token, start date and Activity Review mode.'),
     __('Save, then Discover profiles and select your Wise Business profile.'),
     __('Discover accounts. Open each account you want, select its ERPNext Bank Account and enable its mapping. Leave others unmapped.'),
     __('Enable the connection and click Sync Now. Background sync runs every 15 minutes.'),
     __('Open the activity inbox to review booked amounts. Pause the connection whenever you want to edit mappings.')
    ].forEach(text => $('<li class="mb-2"></li>').text(text).appendTo(steps));
    const actions = $('<div class="my-4 d-flex flex-wrap"></div>').appendTo(content);
    function button(label, action) { $('<button class="btn btn-default mr-2 mb-2"></button>').text(__(label)).on('click',action).appendTo(actions); }
    button('New connection', () => frappe.new_doc('Wise Connection',{mode:'Activity Review',environment:'Production',timezone:'Europe/London',start_date:frappe.datetime.add_days(frappe.datetime.get_today(),-30)}));
    button('Connections', () => frappe.set_route('List','Wise Connection'));
    button('Account mappings', () => frappe.set_route('List','Wise Account Map'));
    button('Activity inbox', () => frappe.set_route('List','Wise Activity',{needs_review:1}));
    button('Source reviews', () => frappe.set_route('List','Wise Booking',{needs_review:1}));
    button('Sync logs', () => frappe.set_route('List','Wise Sync Log'));
    button('Create ERPNext Bank Account', () => frappe.new_doc('Bank Account',{is_company_account:1}));
  };
})();
