<div align="center">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=green" alt="Django" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis" />
  <img src="https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white" alt="Celery" />
  <img src="https://img.shields.io/badge/LangChain-121212?style=for-the-badge&logo=chainlink&logoColor=white" alt="LangChain" />
  <img src="https://img.shields.io/badge/FAISS-0052CC?style=for-the-badge&logo=meta&logoColor=white" alt="FAISS" />
  
  <br />
  <br />

  # 🛒 Velora Next-Gen E-Commerce Platform
  
  **An enterprise-grade, highly scalable e-commerce backend powered by Django 5, Celery, WebSockets, and Generative AI.**
  
  <br />
</div>

---

## ✨ System Architecture & Core Features

Velora isn't just a standard storefront; it's a production-ready engine built with enterprise patterns like strict ACID inventory locking, asynchronous task queues, and real-time AI capabilities.

### 🛡️ Production-Grade Inventory Management
* **ACID Transactions:** Full `transaction.atomic()` wrappers around all checkout and cancellation flows.
* **Concurrency Safety:** Uses PostgreSQL row-level locking (`select_for_update()`) to prevent race conditions. It is physically impossible for two users to buy the last item simultaneously.
* **Idempotent Operations:** `InventoryTransaction` audit log with unique idempotency keys guarantees no double-deductions or infinite stock inflation during network failures.

### ⚙️ Asynchronous Celery Engine (17+ Background Jobs)
The monolithic architecture is broken down into modular background tasks running on Redis:
* **Order Lifecycles:** 10-minute automated cart expirations and 30-minute unpaid COD auto-cancellations (with safe stock restoration).
* **Event-Driven Processing:** Async PDF invoice generation and HTML Order Confirmation Emails.
* **Automated Retries:** SMTP errors trigger exponential backoff retries automatically.
* **Nightly Routines:** Automated `.sql.gz` database backups, FAISS AI embedding cache refreshes, and Search Index rebuilding.
* **Continuous Cleanup:** Automated deletion of expired OTPs, guest carts, unused sessions, orphan temporary images, and expired coupons.

### 🤖 AI-Powered Chatbot & RAG (Retrieval-Augmented Generation)
* **LLM Integrations:** Powered by **Google Gemini** and **Groq** APIs.
* **LangChain & LangGraph:** Stateful conversation routing and tool execution.
* **Semantic Search:** **FAISS** vector database with HuggingFace `sentence-transformers` allows users to search products via natural language embeddings.
* **Persistent Memory:** Uses **MongoDB** to persist long-term chat history per user session.

### 💳 Payments & Checkout
* **Razorpay Integration:** Fully integrated online payment verification.
* **Multi-Tier Checkout:** Supports Online Payment, Cash On Delivery (COD), and eligibility checks.
* **Dynamic Discounts:** Support for Coupons, Membership discounts, and Subscription-based free shipping rules.

### ⚡ Real-Time WebSockets
* **Django Channels + Redis:** Pushes real-time stock notifications and order updates directly to the frontend without polling.

### 🛠️ Comprehensive Admin & Analytics
* **Custom Admin Dashboard:** View real-time revenue, product popularity scores, and active user metrics.
* **Automated Workflows:** Single-click approval for Admin Refunds and Order Cancellations (which seamlessly hooks back into the `InventoryService` for restocking).

---

## 🏗️ Tech Stack

* **Backend Framework:** Django 5.x (ASGI/Daphne)
* **Database:** PostgreSQL (Core) + MongoDB (AI Chat History)
* **Message Broker / Cache:** Redis
* **Task Queues:** Celery + Celery Beat (DatabaseScheduler)
* **AI & Machine Learning:** LangChain, LangGraph, FAISS (faiss-cpu), Sentence-Transformers
* **Payments:** Razorpay API
* **Emails:** SMTP (Gmail)
* **PDF Generation:** xhtml2pdf

---

## 🚀 Quick Start (Development)

### 1. Prerequisites
Ensure you have Python 3.10+, PostgreSQL, Redis, and MongoDB installed and running on your machine.

### 2. Environment Setup
Create a `.env` file in the root directory:
```env
SECRET_KEY=your_django_secret
DEBUG=True
DB_PASSWORD=your_postgres_password
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
MONGO_URI=mongodb://localhost:27017/
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
```

### 3. Installation
```bash
# Clone repository
git clone https://github.com/Rudra-005/E-Commerce-Website.git
cd E-Commerce-Website/myproject

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Seed background tasks (Celery Beat)
python manage.py shell -c "from shop.schedulers.setup_beat import setup_periodic_tasks; setup_periodic_tasks()"
```

### 4. Running the Stack
You will need multiple terminal windows to run the full stack locally:

```bash
# Terminal 1: Django ASGI Server
daphne -b 0.0.0.0 -p 8000 myproject.asgi:application

# Terminal 2: Celery Worker
celery -A myproject worker --loglevel=info --pool=solo -Q default,invoice,email,recommendation,payments,support,analytics

# Terminal 3: Celery Beat (Scheduler)
celery -A myproject beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

---

<div align="center">
  <i>Built for scale. Designed for the future of AI-driven commerce.</i>
</div>
