frappe.ui.form.on('Wise Connection', {
  refresh(frm) {
    const saved = () => {
      if (frm.is_dirty()) {
        frappe.msgprint(__('Save your changes first.'));
        return false;
      }
      return true;
    };
    const openSetup = () => {
      if (!frm.is_new() && !saved()) return;
      frappe.route_options = frm.is_new() ? {new_connection: 1} : {connection: frm.doc.name};
      return frappe.set_route('wise-setup');
    };
    if (frm.is_new()) {
      frm.add_custom_button(__('Guided setup'), openSetup);
      return; // Keep the native Save action on new documents.
    }

    const setupGroup = __('Setup');
    const viewGroup = __('View');
    const statements = frm.doc.mode === 'Statements';
    frm.add_custom_button(__('Continue setup'), openSetup, frm.doc.enabled ? setupGroup : null);
    frm.add_custom_button(__('Manage mappings'), () => {
      frappe.set_route('List', 'Wise Account Map', {connection: frm.doc.name});
    }, setupGroup);

    if (!frm.doc.enabled) {
      frm.change_custom_button_type(__('Continue setup'), null, 'primary');
      frm.add_custom_button(__('Discover profiles'), async () => {
        if (!saved()) return;
        const r = await frappe.call({
          method: 'wise_bank_feed.api.profiles', args: {connection: frm.doc.name}, freeze: true,
        });
        const ids = (r.message || []).map(p => String(p.id));
        if (!ids.length) { frappe.msgprint(__('No Business profiles found.')); return; }
        frappe.prompt([
          {fieldname: 'profile', fieldtype: 'Select', label: __('Business profile'), options: ids, reqd: 1},
        ], async values => {
          await frm.set_value('profile_id', values.profile);
          await frm.save();
        }, __('Select Wise profile'));
      }, setupGroup);
      frm.add_custom_button(__('Discover accounts'), async () => {
        if (!saved()) return;
        if (!frm.doc.profile_id) { frappe.msgprint(__('Select a Business profile first.')); return; }
        await frappe.call({
          method: 'wise_bank_feed.api.discover_accounts', args: {connection: frm.doc.name}, freeze: true,
        });
        frappe.set_route('List', 'Wise Account Map', {connection: frm.doc.name});
      }, setupGroup);
    } else {
      let syncing = false;
      frm.add_custom_button(__('Sync Now'), async () => {
        if (!saved() || syncing) return;
        syncing = true;
        try {
          await frappe.call({
            method: 'wise_bank_feed.api.sync_now', args: {connection: frm.doc.name},
            freeze: true, freeze_message: __('Queuing sync...'),
          });
          frappe.show_alert({message: __('Sync queued. Check Sync logs for progress.'), indicator: 'green'});
        } finally {
          syncing = false;
        }
      });
      frm.change_custom_button_type(__('Sync Now'), null, 'primary');
    }

    frm.add_custom_button(__(statements ? 'Booking records' : 'Activity inbox'), () => {
      frappe.set_route('List', statements ? 'Wise Booking' : 'Wise Activity', {connection: frm.doc.name});
    }, viewGroup);
    frm.add_custom_button(__('Sync logs'), () => {
      frappe.set_route('List', 'Wise Sync Log', {connection: frm.doc.name});
    }, viewGroup);
    frm.dashboard.set_headline_alert(statements
      ? __('Personal-token statements require a supported account region (US, CA, AU, NZ, SG or MY). Access errors leave history unchanged; check Sync logs.')
      : __('Activities sync automatically. Booked entries require review; this mode is not a complete automatic bank feed.'));
  },
});
