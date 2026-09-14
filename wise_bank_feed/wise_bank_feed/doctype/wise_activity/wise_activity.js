frappe.ui.form.on('Wise Activity', {
  refresh(frm) {
    frm.add_custom_button(__('Create reviewed bank entry'), () => {
      frappe.prompt([
        {fieldname:'account_map',fieldtype:'Link',options:'Wise Account Map',label:__('Mapped Wise account'),reqd:1,
         get_query:() => ({filters:{connection:frm.doc.connection,enabled:1,available:1}})},
        {fieldname:'direction',fieldtype:'Select',options:'Deposit\nWithdrawal',label:__('Direction'),reqd:1},
        {fieldname:'value',fieldtype:'Data',label:__('Exact total booked amount in account currency'),reqd:1},
        {fieldname:'booking_date',fieldtype:'Date',label:__('Booking date'),reqd:1},
        {fieldname:'evidence',fieldtype:'Small Text',label:__('Evidence / reference checked in Wise'),reqd:1},
        {fieldname:'confirmed',fieldtype:'Check',label:__('I verified the account, date, direction and total amount including fees'),reqd:1}
      ], async v => {
        const r = await frappe.call({method:'wise_bank_feed.api.create_reviewed_booking',args:{activity:frm.doc.name,expected_hash:frm.doc.payload_hash,...v},freeze:true});
        frappe.set_route('Form','Bank Transaction',r.message);
      }, __('Review before importing'), __('Create Bank Transaction'));
    });
    frm.add_custom_button(__('Finish review'), () => frappe.prompt([
      {fieldname:'note',fieldtype:'Small Text',label:__('Review outcome — include all FX legs or why no entry is needed'),reqd:1}
    ], async v => { await frappe.call({method:'wise_bank_feed.api.finish_review',args:{activity:frm.doc.name,note:v.note,expected_hash:frm.doc.payload_hash}}); frm.reload_doc(); }));
    frm.add_custom_button(__('Booking records'), () => frappe.set_route('List','Wise Booking',{activity:frm.doc.name}));
  }
});
