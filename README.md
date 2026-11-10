# MiniApps Suite 🚀

A modular, multi-agent Python backend ecosystem designed to automate demand scouting, developer code auditing, execution recording, and Stripe-powered payment checkouts.

---

## 🏗️ Architecture & Project Structure

The project follows a decoupled, modular architecture where each autonomous component handles a specific lifecycle stage—from market research and automated code quality reviews to secure transactional processing.

```text
miniapps/
│
├── main.py                  # Core application orchestrator and entry point
├── requirements.txt         # Project dependencies and environment packages
├── .gitignore               # Excluded runtime files and sensitive artifacts
│
└── src/
    ├── 01_demand_scout.py   # Automated market demand and lead scouting module
    ├── 02_developer_qa.py   # Automated code review, auditing, and quality assurance
    ├── 03_demo_recorder.py  # Execution and demonstration recording utility
    ├── 04_sales_stripe.py   # Stripe payment gateway integration and checkout processing
    ├── 05_report.py         # Comprehensive data aggregation and report generator
    ├── common.py            # Shared utility functions and global configurations
    │
    ├── AVISO_IMPORTANTE.md  # Legal notices and compliance guidelines
    ├── README.md            # Internal documentation
    ├── devoluciones.md      # Refund policy terms (Spanish)
    ├── privacidad.md        # Privacy policy documentation (Spanish)
    └── terminos_venta.md    # Terms of sale and service agreements (Spanish)
🛠️ Core Modules Overview
Module	File	Description
Demand Scout	01_demand_scout.py	Scrapes feeds and analyzes target market signals to identify high-value opportunities.
Developer QA	02_developer_qa.py	Performs automated code analysis, checks conventions, and validates structural integrity.
Demo Recorder	03_demo_recorder.py	Captures runtime workflows and interaction logs for demonstrations and auditing.
Sales & Stripe	04_sales_stripe.py	Manages secure payment checkouts, webhook listeners, and transaction workflows via Stripe.
Report Engine	05_report.py	Consolidates outputs from scouts and audits into structured executive summaries.
⚙️ Getting Started & Installation
Prerequisites
Python 3.10 or higher installed on your system.

Active API keys for integrated services (such as Stripe and AI providers).

1. Clone the Repository
Bash
git clone [https://github.com/javiermp96/miniapps.git](https://github.com/javiermp96/miniapps.git)
cd miniapps
2. Set Up a Virtual Environment (Recommended)
Bash
python -m venv venv
# On Windows (PowerShell):
venv\Scripts\Activate
# On macOS/Linux:
source venv/bin/activate
3. Install Dependencies
Bash
pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the root directory and add your required keys (e.g., Stripe API keys, model tokens, database URIs):

Code snippet
STRIPE_API_KEY=your_stripe_secret_key
# Add other necessary environment parameters here
🚀 Usage
Execute the orchestrator or run individual modules directly depending on your pipeline requirements:

Bash
python main.py
To run a specific pipeline script directly:

Bash
python src/01_demand_scout.py
📄 Legal & Compliance
This repository includes standard compliance documents and commercial terms located in the src/ directory:

Terms of Sale (terminos_venta.md)

Privacy Policy (privacidad.md)

Refund Policy (devoluciones.md)

👤 Author
Developed by Javier (@javiermp96).
