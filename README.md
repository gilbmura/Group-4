# Group 4

## Team members

1. MURAMIRABAGABO Gilbert
2. KALISA Auriane
3. IGABE SHAMI Placide

# MoMo SMS Data Processing & Visualization

This project processes **MoMo SMS data (XML format)**, cleans and categorizes transactions, stores them in a relational database, and provides a simple **frontend dashboard** for analytics and visualization.  

It follows an **ETL pipeline** pattern:
1. **Extract** – Parse incoming XML SMS messages.  
2. **Transform** – Clean, normalize, and categorize transaction data.  
3. **Load** – Store structured data in a relational database (SQLite by default).  
4. **Visualize** – Analyze and display data through a web-based dashboard.  

---

## Features

- XML parsing of MoMo SMS data  
- Data cleaning & normalization (amounts, dates, phone numbers)  
- Categorization of transactions (deposit, withdrawal, transfer, bills, etc.)  
- Storage in a relational database (SQLite for development, PostgreSQL optional)  
- Frontend dashboard for **charts, tables, and insights**  
- Modular design: ETL pipeline, API layer, and web UI are separated  

---

## Project Structure

```

.
├── README.md             # Project overview + setup
├── requirements.txt      # Python dependencies
├── .env.example          # Example environment variables
│
├── data/                 # XML input, processed JSON, database, logs
├── etl/                  # ETL pipeline (parse, clean, categorize, load)
├── api/                  # Backend API (optional, FastAPI/Flask)
├── web/                  # Frontend dashboard (HTML, CSS, JS)
├── scripts/              # Helper shell/python scripts
└── tests/                # Unit tests

````

---

## System Architecture

View the system architecture diagram here --> https://drive.google.com/file/d/12Kviqjg_MJxGnNvE9CSRUwOVm7asimPx/view?usp=sharing

---

##  Scrum Board

Access the GitHub project board here --> https://trello.com/b/R0nDRKGQ/momo-etl-sprint-1 

This week we have decided to change our scrum board from Trello and use github as it will be easy to mark our issues as they occur.
---

## Setup & Installation

1. **Clone the repository**
   ```bash
   https://github.com/gilbmura/Group-4.git
   cd Group-4
````

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/Mac
   venv\Scripts\activate      # Windows
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   * Copy `.env.example` → `.env`
   * Update database URL or API port if needed

5. **Run the ETL pipeline**

   ```bash
   python etl/run.py --xml data/raw/momo.xml
   ```

6. **Serve the frontend dashboard**

   ```bash
   python -m http.server 8000
   ```

   Then open [http://localhost:8000/web/index.html](http://localhost:8000/web/index.html) in your browser.

---

## Roadmap

* [ ] Initial ETL pipeline (parse, clean, categorize, load)
* [ ] SQLite database integration
* [ ] Basic frontend dashboard (HTML + JS + charts)
* [ ] Optional backend API with FastAPI
* [ ] Improved analytics (filters, trends, KPIs)
* [ ] Deployment to cloud (Heroku / Render / AWS / etc.)

---

# Testing

Run unit tests with:

```bash
pytest tests/
```

---

# License

This project is licensed under the MIT License.
