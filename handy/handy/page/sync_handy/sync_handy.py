import frappe
import requests
from frappe import _

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
            frappe.throw(_("Error from Handy: {0}").format(response.text))

        data = response.json()
        for c in data.get("customers", []):
            code = c.get("code")
            if not code:
                continue

            vals = {
                "doctype": "Customer",
                "customer_name": c.get("description", "Sin nombre"),
                "customer_type": "Company",
                "customer_group": "Commercial",
                "territory": "All Territories",
                "handy_code": code,
                "email_id": c.get("email"),
                "phone": c.get("phoneNumber"),
                "handy_payment_type": c.get("paymentType"),
                "handy_credit_days": c.get("creditDays", 0),
            }

            existing = frappe.get_all("Customer", filters={"handy_code": code})
            if existing:
                doc = frappe.get_doc("Customer", existing[0]["name"])
                doc.update(vals)
                doc.save(ignore_permissions=True)
            else:
                doc = frappe.get_doc(vals)
                doc.insert(ignore_permissions=True)

            total_synced += 1

        url = data.get("pagination", {}).get("nextPage")

    return {"status": "success", "message": f"✅ Synced {total_synced} customers"}


@frappe.whitelist()
def sync_customers():
  # Your existing logic here...
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
          frappe.throw(_("Error from Handy: {0}").format(response.text))

      data = response.json()
      for c in data.get("customers", []):
          code = c.get("code")
          if not code:
              continue

          vals = {
              "doctype": "Customer",
              "customer_name": c.get("description", "Sin nombre"),
              "customer_type": "Company",
              "customer_group": "Commercial",
              "territory": "All Territories",
              "handy_code": code,
              "email_id": c.get("email"),
              "phone": c.get("phoneNumber"),
              "handy_payment_type": c.get("paymentType"),
              "handy_credit_days": c.get("creditDays", 0),
          }

          existing = frappe.get_all(
              "Customer", filters={"handy_code": code})
          if existing:
              doc = frappe.get_doc("Customer", existing[0]["name"])
              doc.update(vals)
              doc.save()
          else:
              doc = frappe.get_doc(vals)
              doc.insert()

          total_synced += 1

      url = data.get("pagination", {}).get("nextPage")

  return {"status": "success", "message": f"✅ Synced {total_synced} products"}
