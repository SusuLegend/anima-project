# 🧠 AI Virtual Assistant Widget  
*A desktop-based intelligent assistant to centralize productivity, reduce workflow disruption, and help users stay focused.*

---

## 📌 Overview  
The **AI Virtual Assistant Widget** is a lightweight, customizable, desktop-based assistant designed to unify productivity tools into one interactive widget. It minimizes app-switching, manages schedules, tracks tasks, and interacts with users through natural language and simple animations.

This project is developed as part of the **Bachelor of Data Science – Capstone Project**.

---

## 👤 Team Members  

| Jason Adika Tanuwijaya | Core Developer |
| Patrick Faraon Macalagay | UI/UX Designer & Researcher |
| Hung Dat Tran | Developer & Product Management |
---

## 🧩 Problem Statement  
Modern users rely on many disconnected tools—calendars, emails, messaging apps, task trackers—which creates **cognitive overload** and reduces productivity. Constant app-switching disrupts focus and workflow.

The solution: **a single desktop assistant that centralizes daily tasks, reminders, and scheduling with natural language interaction.**

---

## 🎯 Objectives

### 🔹 Primary Objectives
- Centralize meetings, tasks, and schedules in one widget  
- Reduce workflow disruption by minimizing app switching  
- Enhance focus with intelligent suggestions and reminders  
- Provide customizable AI personalities for user engagement  

### 🔹 Secondary Objectives
- Integrate with external tools (Slack, Teams, Trello, Notion APIs, etc.)  
- Implement adaptive learning based on user habits  
- Filter notifications to reduce distractions  
- Improve interaction through conversational AI + visual animation  

---

## 📘 Features (In Scope)
- Desktop floating character widget  
- Natural Language Understanding (10+ core commands)  
- Local LLM (privacy-first)  
- Notification + scheduling system  
- Behavior learning engine (ML-based)  
- MCP (Model Control Protocol) for managing system flow  
- Character animation engine (via Godot)  
- Offline storage via SQLite / TinyDB  

### ❌ Out of Scope
- Advanced visual customization  
- Big Scale Production

---

## 🏗️ Technical Architecture  

The system is composed of 8 core layers:

1. **UI Layer:**  
   Built using **PySide6**, displays floating character + animations  
2. **MCP Layer:**  
   The brain of the system—handles context, tasks, event routing  
3. **AI Brain Layer:**  
   Local LLM via **Ollama**, processes commands & generates responses  
4. **Action Layer:**  
   Executes reminders, launches apps, manages notifications  
5. **Behavior Learning Layer:**  
   Tracks user patterns using pandas + scikit-learn  
6. **Character Engine Layer:**  
   Godot-powered animated desktop companion  
7. **Storage Layer:**  
   Local SQLite / TinyDB for logs, preferences, and history  
8. **Local API Layer:**  
   FastAPI interface for debugging and module communication  

---

## 🛠️ Tools & Technologies  
- **Python 3.10+**, PySide6, asyncio, ZeroMQ, APScheduler  
- **Godot 4**, SQLite, TinyDB  
- **Ollama (local LLM)**  
- **FastAPI**, scikit-learn, pandas  
- Git, GitHub, Markdown, Draw.io, Mermaid  

---

## 📊 Methodology  
The project uses an **Agile development cycle** with iterations across:  
- Core system development  
- Intent parsing  
- AI model integration  
- Behavior tracking  
- Character animation  
- Final testing & optimization  

---

## 🧪 Testing Strategy  
- **Functional Testing**: Validate all modules  
- **Performance Testing**: CPU, memory, and latency checks  
- **Long-duration Reliability**  
- **ML Behavior Learning Accuracy**: Manual labelling and validation  

---

## 📅 Project Timeline  
Includes 5 major phases:

1. **Research & Planning**  
2. **System Design**  
3. **Implementation**  
4. **Testing & Validation**  
5. **Documentation & Presentation**  

Full milestone list is available in the project report.

---

## Note
Playwright install 