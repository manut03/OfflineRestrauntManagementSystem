# 🍽️ Offline Restaurant Management System

An **Offline Restaurant Management System** built using **Python, HTML, CSS, JavaScript, and MySQL**, designed for small restaurants to manage daily operations such as **menu management, billing, inventory tracking, and sales reporting** — all without the need for an internet connection.

---

## 🚀 Features

### 🧾 Billing Module
- Generate and print customer bills.
- Automatically calculates taxes and total amounts.
- Saves billing history in the database.

### 🍴 Menu Module
- Add, update, or remove menu items.
- Automatically updates availability based on inventory.

### 📦 Inventory Module
- Tracks stock levels of ingredients.
- Alerts for low-stock items.
- Updates automatically when items are sold.

### 📊 Reporting Module
- Generates daily and monthly sales reports.
- Displays top-selling items.
- Exports data for business insights.

---

## 🛠️ Tech Stack

- **Frontend:** HTML, CSS, JavaScript  
- **Backend:** Python (Flask Framework)  
- **Database:** MySQL  
- **Tools:** Visual Studio Code, MySQL Workbench  

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/manut03/OfflineRestaurantManagementSystem.git
cd OfflineRestaurantManagementSystem
```

---

### 2️⃣ Set Up a Virtual Environment

```bash
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

---

### 3️⃣ Restore the Database

1. Open **MySQL Workbench** or the command line.  
2. Create the database:

   ```sql
   CREATE DATABASE restaurant_db;
   ```

3. Import the SQL dump:

   ```bash
   mysql -u root -p restaurant_db < database/restaurant.sql
   ```

---

### 4️⃣ Run the Application

```bash
python app.py
```

Now open your browser and go to:  
👉 [http://localhost:5000](http://localhost:5000)

---

## 👨‍💻 Author

**Manasa**  
🌐 [GitHub Profile](https://github.com/manut03)
