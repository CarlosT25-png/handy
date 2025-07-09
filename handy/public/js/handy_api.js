frappe.ui.form.on('Handy API', {
    refresh(frm) {
        frm.add_custom_button(__('Sync Products'), () => {
            frappe.call({
                method: 'handy.handy.doctype.handy_api.handy_api.sync_products',
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint(__('✅ Products synced successfully'));
                    }
                }
            });
        });

        frm.add_custom_button(__('Sync Customers'), () => {
            frappe.call({
                method: 'handy.handy.doctype.handy_api.handy_api.sync_customers',
                callback: function(r) {
                    if (!r.exc) {
                        frappe.msgprint(__('✅ Customers synced successfully'));
                    }
                }
            });
        });
    }
});
