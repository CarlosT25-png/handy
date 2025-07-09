import frappe
import requests
from frappe import _
from datetime import date

@frappe.whitelist()
def sync_customers():
    api_key = frappe.db.get_single_value("Handy API", "handy_api_key")
    base_url = "https://hub.handy.la/api/v2/customer?max=100"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    url = base_url
    total_synced = 0

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            frappe.throw(_("Handy API error: {0} {1}").format(response.status_code, response.text))

        data = response.json()
        customers = data.get("customers", [])

        for c in customers:
            code = c.get("code")
            if not code:
                continue

            # Check for existing customer by handy_code (custom field)
            existing = frappe.get_all("Customer", filters={"handy_code": code})
            doc = frappe.get_doc("Customer", existing[0].name) if existing else frappe.new_doc("Customer")

            # Prepare values
            doc.customer_name = c.get("description", "Sin nombre")
            doc.handy_code = code  # Custom field
            doc.customer_group = "Commercial"
            # doc.territory = "All Territories"
            doc.customer_type = "Company"
            doc.phone = c.get("phoneNumber", "")
            doc.email_id = c.get("email", "")
            doc.disabled = not c.get("enabled", True)

            # Optional: custom fields (you must define these in ERPNext)
            doc.handy_payment_type = c.get('paymentType')
            # doc.handy_payment_default = c.get('paymentTypeDefault')
            # doc.handy_credit_days = c.get('creditDays', 0)
            # doc.handy_sale_threshold = c.get('effectiveSaleThreshold', 0.0)
            doc.latitude = c.get("latitude")
            doc.longitude = c.get("longitude")
            doc.zone_id = c.get("zone", {}).get("id")
            doc.zone_name = c.get("zone", {}).get("description")

            category = c.get("category", {}).get("description")
            if category:
                if not frappe.db.exists("Customer Group", category):
                    frappe.get_doc({
                        "doctype": "Customer Group",
                        "customer_group_name": category
                    }).insert(ignore_permissions=True)
                doc.customer_group = category

            # Save or update
            if existing:
                doc.save(ignore_permissions=True)
            else:
                doc.insert(ignore_permissions=True)

            total_synced += 1

        url = data.get("pagination", {}).get("nextPage")

    return {
        "status": "success",
        "message": _("✅ Se sincronizarón {0} clientes desde Handy.").format(total_synced)
    }


@frappe.whitelist()
def sync_products():
    api_key = frappe.db.get_single_value("Handy API", "handy_api_key")
    base_url = "https://hub.handy.la/api/v2/product?max=100"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Try to get the root item group
    root_group = frappe.db.get_value("Item Group", {"parent_item_group": ""}, "name")
    if not root_group:
        frappe.throw(_("No root Item Group found. Please create one first."))

    url = base_url
    total_synced = 0

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            frappe.throw(_("Error from Handy: {0}").format(response.text))

        data = response.json()
        for p in data.get("products", []):
            uom_code = p.get("unit", {}).get("code", "Unidad")
            if not frappe.db.exists("UOM", uom_code):
                frappe.get_doc({
                    "doctype": "UOM",
                    "uom_name": uom_code
                }).insert(ignore_permissions=True)

            # Handle Item Group
            item_group = p.get("category", {}).get("description", root_group)
            if not frappe.db.exists("Item Group", item_group):
                frappe.get_doc({
                    "doctype": "Item Group",
                    "item_group_name": item_group,
                    "parent_item_group": root_group
                }).insert(ignore_permissions=True)

            doc = frappe.get_doc({
                "doctype": "Item",
                "item_code": p["code"],
                "item_name": p.get("description", "No name"),
                "stock_uom": uom_code,
                "standard_rate": p.get("price", 0.0),
                "barcode": p.get("barcode"),
                "item_group": item_group
            })

            try:
                doc.insert(ignore_if_duplicate=True, ignore_permissions=True)
            except frappe.DuplicateEntryError:
                existing = frappe.get_doc("Item", p["code"])
                existing.update(doc)
                existing.save(ignore_permissions=True)

            total_synced += 1

        url = data.get("pagination", {}).get("nextPage")

    return {"status": "success", "message": f"✅ Se sincronizarón {total_synced} productos desde Handy."}

@frappe.whitelist()
def sync_price_lists():
    api_key = frappe.db.get_single_value("Handy API", "handy_api_key")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. Fetch all Handy price lists
    handy_price_lists = {}
    url = "https://hub.handy.la/api/v2/priceList?page=1"

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            frappe.throw(_("Handy API error: {0} {1}").format(response.status_code, response.text))

        data = response.json()
        for price_list in data.get("priceLists", []):
            handy_price_lists[price_list["code"]] = price_list["id"]

        url = data.get("pagination", {}).get("nextPage")

    # 2. Get all ERP Price Lists
    erp_price_lists = frappe.get_all("Price List", fields=["name", "enabled"])

    for pl in erp_price_lists:
        code = pl["name"]

        # 3. Get items and prices from ERP Price List
        items_data = frappe.get_all(
            "Item Price",
            filters={"price_list": pl["name"]},
            fields=["item_code", "price_list_rate"]
        )

        items = []
        for item in items_data:
            items.append({
                "product": item["item_code"],
                "price": item["price_list_rate"]
            })

        payload = {
            "name": pl["name"],
            "code": code,
            "items": items
        }

        if code in handy_price_lists:
            # Update existing
            handy_id = code
            update_url = f"https://hub.handy.la/api/v2/priceList/{handy_id}"
            r = requests.put(update_url, headers=headers, json=payload)
        else:
            # Create new
            create_url = "https://hub.handy.la/api/v2/priceList"
            r = requests.post(create_url, headers=headers, json=payload)

        if r.status_code not in (200, 201):
            frappe.log_error(f"{r.status_code} {r.text}", "Error al sincronizar lista de precios")
            
    return {"status": "success", "message": f"ERPNext ha sincronizado las listas de precios con Handy."}

@frappe.whitelist()
def create_stock_movement(doc, method):
    WAREHOUSES_TO_WATCH = ["Ruta 227", "Ruta 228", "Ruta 229", "Ruta 230", "Ruta 231"]

    if doc.purpose != "Material Transfer":
        return

    api_key = frappe.db.get_single_value("Handy API", "handy_api_key")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 1. Load all open routes
    routes_url = "https://hub.handy.la/api/v2/route?closed=false&max=100"
    route_response = requests.get(routes_url, headers=headers)
    if route_response.status_code != 200:
        frappe.throw(_("Handy API error: {0} {1}").format(route_response.status_code, route_response.text))

    routes_data = route_response.json().get("routes", [])

    # 2. Map warehouse name to Handy user ID
    warehouse_to_user_id = {}
    for route in routes_data:
        user = route.get("user")
        if user and user.get("name") in WAREHOUSES_TO_WATCH:
            warehouse_to_user_id[user["name"]] = user["id"]

    # 3. Group ERP items by warehouse
    grouped_products = {}
    for item in doc.items:
        warehouse = item.t_warehouse.split(" - ")[0]  # Remove suffix like " - D"
        if warehouse in WAREHOUSES_TO_WATCH:
            grouped_products.setdefault(warehouse, []).append({
                "product": item.item_code,
                "quantity": item.qty
            })

    # 4. Create missing routes with products
    for warehouse, products in grouped_products.items():
        if warehouse not in warehouse_to_user_id:
            # Look up user ID
            user_lookup_url = f"https://hub.handy.la/api/v2/user?name={warehouse}"
            user_lookup_response = requests.get(user_lookup_url, headers=headers)
            if user_lookup_response.status_code != 200:
                frappe.throw(_("Failed to look up user for {0}: {1}").format(
                    warehouse, user_lookup_response.text
                ))

            users = user_lookup_response.json().get("users", [])
            if not users:
                frappe.throw(_(f"User {warehouse} not found in Handy"))

            user_id = users[0]["id"]

            # Create the route with products
            create_route_payload = {
                "initialAmount": 0.0,
                "comments": f"Creado automaticamente para {warehouse}",
                "salesOrders": [],
                "products": products,
            }
            create_route_url = f"https://hub.handy.la/api/v2/user/{user_id}/route?prettyMessages=true"
            create_route_response = requests.post(create_route_url, headers=headers, json=create_route_payload)

            if create_route_response.status_code not in (200, 201):
                frappe.throw(_("Failed to create route for {0}: {1}").format(
                    warehouse, create_route_response.text
                ))

            warehouse_to_user_id[warehouse] = user_id

        else:
            # 5. Recharge existing route
            user_id = warehouse_to_user_id[warehouse]
            recharge_payload = {
                "products": products
            }

            recharge_url = f"https://hub.handy.la/api/v2/user/{user_id}/route/recharge"
            recharge_response = requests.post(recharge_url, headers=headers, json=recharge_payload)

            if recharge_response.status_code not in (200, 201):
                frappe.log_error(
                    f"Failed to recharge route for {warehouse} (user {user_id}): {recharge_response.status_code} {recharge_response.text}",
                    "Handy Recharge Error"
                )
            else:
                frappe.logger().info(f"Recharged {len(products)} products to {warehouse} (user {user_id})")

@frappe.whitelist()
def sync_products_quantities():
    print("Running sync_products_quantities at scheduled time")
    api_key = frappe.db.get_single_value("Handy API", "handy_api_key")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    base_url = "https://hub.handy.la/api/v2/product?max=100"
    url = base_url
    
    # 1. Obtener todos los productos de Handy (paginación)
    handy_products = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            frappe.throw(_("Error en la API de Handy: {0} {1}").format(response.status_code, response.text))
        
        data = response.json()
        handy_products.extend(data.get("products", []))
        pagination = data.get("pagination", {})
        url = pagination.get("nextPage")

    # 2. Crear diccionario código_producto_handy -> producto
    handy_products_dict = {p["code"]: p for p in handy_products}

    # 3. Obtener productos de ERPNext con cantidad en stock
    erp_products = frappe.get_all("Bin", 
                                  filters={"warehouse": "Bodega - D"},
                                 fields=["item_code", "actual_qty"])
    
    # 4. Actualizar cantidad en Handy si el producto existe
    for erp_product in erp_products:
        code = erp_product["item_code"]
        quantity = erp_product["actual_qty"]
        
        if code not in handy_products_dict:
            frappe.log_error(f"Producto con código {code} no encontrado en Handy", "Advertencia Sincronización Productos")
            continue
        
        handy_product = handy_products_dict[code]
        
        # Payload para actualizar cantidad
        update_url = f"https://hub.handy.la/api/v2/product/{code}"
        payload = {
            "quantity": quantity
        }
        
        update_response = requests.put(update_url, headers=headers, json=payload)
        if update_response.status_code not in (200, 201):
            print(
                f"No se pudo actualizar la cantidad para el producto {code}: {update_response.status_code} {update_response.text}",
                "Error Actualización Producto Handy"
            )