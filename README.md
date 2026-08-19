# G&C Central Deal and Brokerage Automation Platform

A secure, responsive, full-stack web application designed for **Ganesh & Company (G&C)**, an edible-oil commodity brokerage. The platform serves as the central automation engine for single-entry deal management, multi-hop resale tracking, price-difference profit calculations, dual-party brokerage, automated resolution of direct commercial billing instructions, professional Excel (`.xlsx`) export with strict A:G column preservation, and future integration with BUSY accounting software.

---

## 🌟 Key Capabilities

### 1. Single-Entry Deal Capture & Chaining
- Broker enters each root deal once with full validation.
- Prominent **"Resell / Add Next Deal"** workflow allows seamlessly adding intermediate links as parties instruct the broker to resell their commitments.
- Maintains complete internal deal-chain history while continuously resolving the **Official Direct Commercial Billing Mandate** (Original Bill Seller ➔ Final Bill Buyer).

### 2. Exact Decimal Financial Calculations
All financial computations use fixed-point decimal arithmetic (`decimal.Decimal` in the backend):
- **Unit Conversions**: `1 Metric Tonne = 10 Quintals = 1,000 Kilograms`.
- **Price-Difference Margin**:
  $$\text{Price Difference per Qtl} = \text{Actual Sale Rate} - \text{Authorized Rate}$$
  $$\text{Price Difference Profit} = \text{Price Difference per Qtl} \times \text{Quantity in Quintals}$$
- **Dual-Party Brokerage (₹ / Metric Tonne)**:
  $$\text{Buyer Brokerage} = \text{Quantity in Tonnes} \times \text{Buyer Brokerage Rate per Tonne}$$
  $$\text{Seller Brokerage} = \text{Quantity in Tonnes} \times \text{Seller Brokerage Rate per Tonne}$$
  $$\text{Total Brokerage} = \text{Buyer Brokerage} + \text{Seller Brokerage}$$
- **Total Chain Earnings**:
  $$\text{Total Earning} = \sum \text{Price Difference Profit} + \sum \text{Deal Brokerage}$$

### 3. Official Direct Billing Instruction Resolution
At every step in a resale chain, the platform resolves the official commercial billing instruction:
> **`[Original Bill Seller]` will issue a direct bill to `[Final Bill Buyer]` for `[Quantity]` quintals of `[Product]` at `₹[Final Rate] + GST` per quintal.**

### 4. Excel Automation Engine
Generates multi-sheet `.xlsx` workbooks with professional formatting, formulas, and auto-adjusted column widths.
**Sheet 1 ("Deals") strictly preserves columns A through G**:
- `A` = Deal/Seller Date (`DD/MM/YYYY`)
- `B` = Buyer
- `C` = Seller
- `D` = Product (e.g. `M.OIL`)
- `E` = Quantity (`32 MT (320 Qtl)`)
- `F` = Price and GST (`15,700 + GST`)
- `G` = Delivery Date (`DD/MM/YYYY`)
- `H+` = Extended analytical & technical fields (Deal ID, Chain ID, Tonnes, Rate/Qtl, GST %, Authorized Rate, Actual Rate, Price Diff/Qtl, Price Diff Profit, Buyer Brok Rate, Buyer Brok Amount, Seller Brok Rate, Seller Brok Amount, Total Brokerage, Total Earning, Status, Original Seller, Final Buyer, Created By, Created At).

### 5. Future BUSY Accounting Integration Adapter
- Staging queue with status tracking (`staged`, `approved`, `posted`, `failed`).
- Standard BUSY XML & intermediate JSON voucher generator for Direct Sales Invoices and Brokerage Commission Journals.
- **Safety Isolation**: Internal intermediate chain deals cannot accidentally be posted as official commercial sales invoices.
- Configurable Party Ledger ID and Product Item ID mappings.

### 6. Role-Based Access Control & Immutable Audit Trail
- Granular permissions for `admin`, `broker`, `accounts`, and `viewer`.
- Immutable audit log capturing before-and-after JSON state diffs for all creates, edits, cancellations, approvals, and sync dispatches.
- Soft cancellation requiring a mandatory audit reason.

---

## 🧪 Acceptance Test Scenario Verification

The platform was built and verified against the mandatory worked scenario:
1. **Initial Purchase (01/07/2026)**:
   - Buyer: `HARYANA INDUSTRIES, PANCHKULA`
   - Seller: `NAGPAL ENTERPRISES PVT. LTD., ANOUPGARH`
   - Product: `M.OIL`, Quantity: `320 Quintals (32 Metric Tonnes)`, Rate: `₹15,700 + GST / Qtl`, Delivery: `31/07/2026`.
2. **First Resale Link (18/07/2026)**:
   - `HARYANA INDUSTRIES` authorizes selling rate of `₹16,450 / Qtl`.
   - Broker sells to `M.L. NAGPAL INDUSTRIES, ANOUPGARH` @ `₹16,475 + GST / Qtl`.
   - Price Difference: `+₹25 / Qtl` $\rightarrow$ **Profit = ₹8,000.00**.
   - Brokerage: Calculated separately on both sides.
3. **Second Resale Link (30/07/2026)**:
   - `M.L. NAGPAL INDUSTRIES` authorizes selling rate of `₹16,475 / Qtl`.
   - Broker sells to `SHAKTI NUTRITIONS PVT. LTD.` @ `₹16,700 + GST / Qtl` (Delivery: 11/08/2026).
   - Price Difference: `+₹225 / Qtl` $\rightarrow$ **Profit = ₹72,000.00**.
4. **Verified Aggregates**:
   - Total Price-Difference Profit: **₹80,000.00**
   - Final Billing Rate: **₹16,700.00 + GST / Qtl**
   - Official Billing Mandate: **`NAGPAL ENTERPRISES PVT. LTD., ANOUPGARH` (or `HARYANA INDUSTRIES`) will issue a direct bill to `SHAKTI NUTRITIONS PVT. LTD.` for `320 quintals` of `M.OIL` at `₹16,700 + GST` per quintal.**

---

## 🚀 Running Locally

### Prerequisites
- Python 3.9+ (with built-in `sqlite3` and `xlsxwriter` package)

### Start the Application Server
Run the backend server directly from the workspace root:
```bash
python3 backend/app.py
```
Open your browser and navigate to:
```
http://localhost:8000
```

### Run the Automated Test Suite
```bash
python3 backend/tests.py
```
You can also run and inspect live test results directly from the **Acceptance Test Suite** tab in the web user interface!

---

## 📂 Project Architecture

```
GaneshAndCompany/
├── backend/
│   ├── app.py                     # HTTP server, REST API router & static asset server
│   ├── database.py                # SQLite database manager with WAL mode & migrations
│   ├── calculations.py            # Exact Decimal arithmetic & chain aggregation engine
│   ├── models.py                  # Schemas, validation rules, and date/currency formatters
│   ├── excel_exporter.py          # Multi-tab XLSX generator preserving A:G columns
│   ├── busy_adapter.py            # BUSY accounting software adapter & voucher builder
│   ├── auth_audit.py              # RBAC session manager & immutable before/after diff audit logger
│   ├── seed_data.py               # Master seed data & pre-loaded acceptance test scenario
│   └── tests.py                   # Automated unit & acceptance test suite
├── frontend/
│   ├── index.html                 # Modern SPA container with topbar & role switcher
│   ├── css/
│   │   ├── design-system.css      # Design tokens, typography, glassmorphism cards, responsive grid
│   │   ├── components.css         # Timeline stepper, direct billing banner, KPI cards, modals
│   │   └── animations.css         # Micro-interactions and status glows
│   └── js/
│       ├── api.js                 # Network API client
│       ├── store.js               # Reactive store, formatters & permissions helper
│       ├── app.js                 # App bootstrapper & tab router
│       └── components/
│           ├── dashboard.js       # KPI metrics, delivery alert tracker & recent deals
│           ├── deal_form.js       # Fast keyboard-friendly deal entry & live preview
│           ├── chain_view.js      # Visual timeline, direct billing card & resale modal
│           ├── party_ledger.js    # Party directory, brokerage statement & payment receipts
│           ├── product_master.js  # Edible oil catalog & HSN/GST settings
│           ├── reports.js         # 10 filterable reports with instant XLSX export
│           ├── busy_settings.js   # BUSY ledger/item mappings & staging queue
│           ├── audit_viewer.js    # Immutable audit trail with state diff inspector
│           └── test_runner.js     # Live acceptance test runner & verification UI
└── README.md                      # Platform documentation
```
