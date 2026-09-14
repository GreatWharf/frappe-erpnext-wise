frappe.ui.form.on('Wise Booking', {
  refresh(frm) {
    if (!frm.doc.needs_review) return;
    frm.add_custom_button(__('Acknowledge source change'), () => frappe.prompt([
      {fieldname:'note',fieldtype:'Small Text',label:__('How were accounting differences and reconciliations resolved?'),reqd:1}
    ], async v => { await frappe.call({method:'wise_bank_feed.api.acknowledge_change',args:{booking:frm.doc.name,note:v.note,expected_hash:frm.doc.latest_hash || frm.doc.source_hash}}); frm.reload_doc(); }));
    frm.dashboard.set_headline_alert(__('Source changed. Original amounts are retained. Review the source revisions and record any required accounting adjustment before acknowledging.'));
  }
});
