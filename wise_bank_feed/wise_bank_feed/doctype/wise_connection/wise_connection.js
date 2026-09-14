frappe.ui.form.on('Wise Connection', {
  refresh(frm) {
    frm.add_custom_button(__('Guided setup'), () => frappe.set_route('wise-setup'));
    if (frm.is_new()) return;
    frm.add_custom_button(__('Discover profiles'), async () => {
      if (frm.is_dirty()) { frappe.msgprint(__('Save first.')); return; }
      const r = await frappe.call({method:'wise_bank_feed.api.profiles',args:{connection:frm.doc.name}});
      const ids = (r.message || []).map(p => String(p.id));
      if (!ids.length) { frappe.msgprint(__('No Business profiles found.')); return; }
      frappe.prompt([{fieldname:'profile',fieldtype:'Select',label:__('Business profile'),options:ids,reqd:1}],
        async v => { await frm.set_value('profile_id',v.profile); await frm.save(); }, __('Select Wise profile'));
    });
    frm.add_custom_button(__('Discover accounts'), async () => {
      if (frm.is_dirty()) { frappe.msgprint(__('Save first.')); return; }
      await frappe.call({method:'wise_bank_feed.api.discover_accounts',args:{connection:frm.doc.name},freeze:true});
      frappe.set_route('List','Wise Account Map',{connection:frm.doc.name});
    });
    frm.add_custom_button(__('Manage mappings'), () => frappe.set_route('List','Wise Account Map',{connection:frm.doc.name}));
    frm.add_custom_button(__('Sync Now'), () => frappe.call({method:'wise_bank_feed.api.sync_now',args:{connection:frm.doc.name}}).then(() => frappe.show_alert(__('Sync queued'))));
    frm.add_custom_button(__('Activity inbox'), () => frappe.set_route('List','Wise Activity',{connection:frm.doc.name}));
    frm.add_custom_button(__('Sync logs'), () => frappe.set_route('List','Wise Sync Log',{connection:frm.doc.name}));
    frm.dashboard.set_headline_alert(frm.doc.mode === 'Activity Review'
      ? __('Activities sync automatically. Booked entries require review; this mode is not a complete automatic bank feed.')
      : __('Personal-token statements require a supported account region (US, CA, AU, NZ, SG or MY). Access errors leave history unchanged; check Sync logs.'));
  }
});
