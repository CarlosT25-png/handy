frappe.pages['sync-handy'].on_page_load = function (wrapper) {
    new PageContent(wrapper)
}

PageContent = Class.extend({
    init: function (wrapper) {
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: 'Sincronización Handy',
            single_column: true
        });

        this.make()
        this.bind_events()
    },

    make: function () {
        let htmlContent = `
        <div class="container">
            <h3>Handy Sync</h3>
            <button id="fetch-customers" class="btn btn-primary">Sincronizar Clientes</button>
            <button id="fetch-products" class="btn btn-secondary">Sincronizar Productos</button>
            <button id="fetch-price-list" class="btn btn-secondary">Sincronizar Lista de Precios</button>
            <div id="status" style="margin-top: 20px;"></div>
        </div>
        `
        $(frappe.render_template(htmlContent, this)).appendTo(this.page.main)
    },

    bind_events: function () {
        let me = this
        $('#fetch-customers').on('click', function () {
            $('#status').html('Fetching customers...')
            frappe.call({
                method: 'handy.handy.api.sync_customers',
                callback: function (r) {
                    if (!r.exc && r.message && r.message.status === 'success') {
                        $('#status').html(`Clientes sincronizados correctamente! ${r.message.message}`)
                    } else {
                        $('#status').html('Error fetching customers.')
                    }
                }
            })
        })

        $('#fetch-products').on('click', function () {
            $('#status').html('Fetching products...')
            frappe.call({
                method: 'handy.handy.api.sync_products',
                callback: function (r) {
                    if (!r.exc && r.message && r.message.status === 'success') {
                        $('#status').html(`Productos sincronizados correctamente! ${r.message.message}`)
                    } else {
                        $('#status').html('Error fetching products.')
                    }
                }
            })
        })

        $('#fetch-price-list').on('click', function () {
            $('#status').html('Sincronizando Lista de Precios...')
            frappe.call({
                method: 'handy.handy.api.sync_price_lists',
                callback: function (r) {
                    if (!r.exc && r.message && r.message.status === 'success') {
                        $('#status').html(`${r.message.message}`)
                    } else {
                        $('#status').html('Error sincronizando lista de precios.')
                    }
                }
            })
        })
    }
})
