from flask import Flask, render_template, request, make_response, redirect, url_for
import math
import base64
import os
from playwright.sync_api import sync_playwright

app = Flask(__name__)

# A simple cache to hold invoice data between the preview and download steps
INVOICE_DATA_CACHE = {}

def number_to_words(n):
    # ... (your existing number_to_words function, no changes here)
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
            "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def words(num):
        if num < 20:
            return ones[num]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 != 0 else "")
        elif num < 1000:
            return ones[num // 100] + " Hundred " + (words(num % 100) if num % 100 != 0 else "")
        elif num < 100000:
            return words(num // 1000) + " Thousand " + (words(num % 1000) if num % 1000 != 0 else "")
        elif num < 10000000:
            return words(num // 100000) + " Lakh " + (words(num % 100000) if num % 100000 != 0 else "")
        else:
            return words(num // 10000000) + " Crore " + (words(num % 10000000) if num % 10000000 != 0 else "")

    return words(n).strip()

def get_invoice_data(form):
    """Helper function to process form data and calculate totals."""
    data = {
        "invoice_no": form.get("invoice_no") or "",
        "invoice_date": form.get("invoice_date") or "",
        "buyer_order_no": form.get("buyer_order_no") or "",
        "supply_date": form.get("supply_date") or "",
        "transporter_name": form.get("transporter_name") or "",
        "vehicle_no": form.get("vehicle_no"),
        "gr_no": form.get("gr_no") or "",
        "company": {
            "name": "Select Media House", "gstin": "09AFMPG9060R1ZK",
            "address": "A-6, Sarla Bagh Extension, Dayal Bagh, Agra - 282005 (U.P.)", "phone": "9837346250",
            "bank_details": "Bank : Canara Bank, MG Road, Agra\nIFSC Code:- CNRB0000192 A/c : 0192201001908"
        },
        "billed_to": { "name": form.get("client_name") or "", "address": form.get("client_address") or "", "state": form.get("client_state") or "", "state_code": form.get("client_state_code") or "", "gstin": form.get("client_gstin") or "" },
        "shipped_to": { "name": form.get("ship_name") or "", "address": form.get("ship_address") or "", "state": form.get("ship_state") or "", "state_code": form.get("ship_state_code") or "", "gstin": form.get("ship_gstin") or "" },
        "discount": float(form.get("discount", 0)), "subtotal": 0.0, "cgst_rate": float(form.get("cgst_rate", 0)), "sgst_rate": float(form.get("sgst_rate", 0)), "igst_rate": float(form.get("igst_rate", 0)), "cgst_amount": 0.0, "sgst_amount": 0.0, "igst_amount": 0.0, "round_off": 0.0, "grand_total": 0.0,
        "amount_in_words": "Rupees only", "reference_no": form.get("reference_no") or "N/A",
    }
    
    line_items = []
    desc_list, hsn_list, qty_list, uom_list, rate_list = form.getlist("item_desc[]"), form.getlist("item_hsn[]"), form.getlist("item_qty[]"), form.getlist("item_uom[]"), form.getlist("item_rate[]")
    for i in range(len(desc_list)):
        if desc_list[i].strip() == "": continue
        qty, rate = float(qty_list[i] or 0), float(rate_list[i] or 0)
        line_items.append({ "description": desc_list[i], "hsn": hsn_list[i], "qty": qty, "uom": uom_list[i], "rate": rate, "amount": qty * rate })
    
    FIXED_ITEM_ROWS = 8
    line_items = line_items[:FIXED_ITEM_ROWS]
    while len(line_items) < FIXED_ITEM_ROWS:
        line_items.append({ "description": "", "hsn": "", "qty": None, "uom": "", "rate": None, "amount": None })
    data["line_items"] = line_items
    
    subtotal = sum(it["amount"] for it in data["line_items"] if it["amount"] is not None) - data["discount"]
    cgst_amount, sgst_amount, igst_amount = subtotal * data["cgst_rate"] / 100, subtotal * data["sgst_rate"] / 100, subtotal * data["igst_rate"] / 100
    grand_total = subtotal + cgst_amount + sgst_amount + igst_amount
    total_tax = cgst_amount + sgst_amount + igst_amount
    rounded_total = math.floor(grand_total)
    round_off = rounded_total - grand_total
    
    data.update({
        "subtotal": subtotal, "cgst_amount": cgst_amount, "sgst_amount": sgst_amount, 
        "igst_amount": igst_amount, "grand_total": rounded_total, "total_tax": total_tax, 
        "round_off": round_off, "amount_in_words": f" {number_to_words(int(rounded_total))} Rupees Only"
    })

    # --- Encode logo image to Base64 to embed in the template ---
    logo_path = os.path.join(app.root_path, 'static', 'img', 'logo.png')
    try:
        with open(logo_path, "rb") as image_file:
            encoded_logo = base64.b64encode(image_file.read()).decode('utf-8')
        data["encoded_logo"] = encoded_logo
    except FileNotFoundError:
        data["encoded_logo"] = None
        print(f"Warning: Logo file not found at {logo_path}")
        
    return data

@app.route("/")
def home():
    return '''
    <div style="height: 100vh; display: flex; flex-direction: column; justify-content: center; align-items: center; font-family: sans-serif; background-color: #f4f6f8;">
        
        <h1 style="color: #2c3e50; font-size: 3rem; font-weight: bold; text-align: center; margin: 0; padding: 0 20px; text-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
            Welcome Select Media House
        </h1>

        <a href="/new-invoice" style="margin-top: 40px; background-color: #3cd6e7; color: white; padding: 25px 60px; font-size: 1.8rem; text-decoration: none; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 15px rgba(231, 76, 60, 0.4);">
            New Invoice
        </a>

    </div>
    '''
@app.route("/new-invoice", methods=["GET", "POST"])
def new_invoice():
    if request.method == "POST":
        # Process the form data
        invoice_data = get_invoice_data(request.form)
        invoice_no = invoice_data["invoice_no"]
        
        # Store the data in our simple cache
        INVOICE_DATA_CACHE[invoice_no] = invoice_data
        
        # Redirect to the new preview route
        return redirect(url_for('preview_invoice', invoice_no=invoice_no))
    
    # GET request: check if we are editing an existing invoice
    invoice_no = request.args.get("invoice_no")
    data = {}
    if invoice_no:
        data = INVOICE_DATA_CACHE.get(invoice_no, {})
        
    return render_template("new_invoice.html", data=data)

@app.route("/preview/<invoice_no>")
def preview_invoice(invoice_no):
    invoice_data = INVOICE_DATA_CACHE.get(invoice_no)
    if not invoice_data:
        return "Invoice data not found or expired. Please create it again.", 404

    # Render the invoice HTML into a string
    invoice_html = render_template("invoice_pdf.html", **invoice_data)
    
    # Render the preview page, embedding the invoice HTML
    return render_template("preview.html", invoice_no=invoice_no, invoice_html=invoice_html)

@app.route("/generate-pdf/<invoice_no>")
def generate_pdf(invoice_no):
    invoice_data = INVOICE_DATA_CACHE.get(invoice_no)
    if not invoice_data:
        return "Invoice data not found or expired. Please create it again.", 404

    # Render the final HTML for PDF generation
    rendered_html = render_template("invoice_pdf.html", **invoice_data)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(rendered_html)
        pdf_content = page.pdf(format='A4', print_background=True)
        browser.close()

    # Clean up the cache after generating the PDF
    if invoice_no in INVOICE_DATA_CACHE:
        del INVOICE_DATA_CACHE[invoice_no]
        
    # Create the downloadable response
    invoice_filename = f"{invoice_data['invoice_no']}_{invoice_data['invoice_date']}.pdf"
    response = make_response(pdf_content)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={invoice_filename}'
    
    return response

if __name__ == "__main__":
    app.run(debug=True)