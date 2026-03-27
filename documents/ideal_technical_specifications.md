# **Citizens Advice AI Information Retrieval Chatbot Technical Specification**

# **1\. Introduction**

## **1.1 Overview**

Citizens Advice services are experiencing increasing demand, making it difficult for staff to efficiently retrieve reliable, case-specific information. Relevant data is distributed across multiple trusted sources, including legal documents, council policies, and guidance materials. This results in time-consuming information retrieval, inconsistent advice quality, and slower decision-making.

This project aims to develop an AI-enabled advisory assistant that consolidates verified information and provides context-aware, source-grounded responses to user queries.

## **1.2 Objectives**

The system is designed to:

* Retrieve information from trusted datasets  
* Identify and rank relevant content  
* Generate context-aware responses  
* Provide transparent, source-backed answers  
* Maintain basic conversational context per case

**1.3 Scope (MVP)**:

* Retrieval-Augmented Generation (RAG) pipeline  
* Case-based query handling  
* Source citation in responses  
* Adjustable response depth (Quick/Standard/Deep)  
* Basic conversation memory  
* Advisor Authentication (via Microsoft Entra ID)

**Stretch Goals**

The following features are stretch goals:

* Automated note taking from phone calls  
* Voice to text prompting  
* Advanced ranking models  
* Complex UI enhancements

# **2\. System Architecture**

**2.1 High-Level Architecture** 

The system follows a modular architecture comprising a frontend interface, a backend API, and a highly secure AI-driven retrieval pipeline. The infrastructure is split between secure cloud hosting and high-performance computing to optimise resources.

Frontend (React \- MSAL.js for Authentication)   
↓  
FastAPI Backend (Python \- Hosted on Azure Virtual Machine)   
↓  
RAG Pipeline   
↓  
Vector Database (FAISS \- Generated on Iridis HPC, Hosted on Azure VM)   
↓  
Enterprise LLM API (Azure OpenAI \- Strict Zero-Retention)

**2.2 Architectural Rationale** 

A Python-based architecture is selected due to its strong ecosystem for machine learning and natural language processing. To comply with data protection requirements, public consumer-tier LLM APIs are strictly prohibited. The architecture mandates Azure OpenAI, ensuring prompts and case data are not logged, stored, or used for model training. To maximize the project budget, heavy computational tasks are offloaded to external HPC clusters, while continuous service availability is maintained via lightweight Azure infrastructure.

# **3\. System Components**

## **3.1 Frontend**

The frontend provides a user interface for interacting with the system.

**Authentication:** Integration with Microsoft Authentication Library (MSAL.js) to provide individual advisor logins via Microsoft Entra ID.

### Features:

* Query input field  
* Case selection panel  
* Response display (answer \+ sources)  
* Depth toggle (Quick / Standard /  Deep)

### Technologies:

* React.js  
* TailwindCSS

## **3.2 Backend (FastAPI)**

### Responsibilities:

* Handle API requests  
* Manage case data  
* Maintain conversation memory  
* Orchestrate the RAG pipeline

## **3.3 AI Retrieval Pipeline (RAG)**

### **Updated Specification Section**

**3.3.1 Data Ingestion (Web Scraping Pipeline)** Data ingestion will be handled via an automated web scraping pipeline targeting a pre-approved whitelist of trusted domains (e.g., citizensadvice.org.uk, gov.uk).

* **Scraping Framework:** The system will utilise Python libraries such as *BeautifulSoup* (for static HTML) and *Playwright* or *Selenium* (if rendering JavaScript-heavy pages is required) to extract content.  
* **Content Cleaning (Boilerplate Removal):** Raw HTML will be stripped of irrelevant structural elements (navigation bars, footers, cookie banners, and sidebars), ensuring that only the core advisory text is passed into the chunking phase. This prevents the AI from generating answers based on website menus.  
* **Metadata Tagging:** Extracted text will be permanently tagged with its Source URL and a *last\_scraped* timestamp. This allows the frontend to provide clickable citation links directly to the original web page.  
* **Automated Syncing:** A scheduled CRON job runs periodically (e.g., weekly) to re-scrape the whitelisted sites, identify updated pages or dead links, and update the vector database accordingly to prevent advice decay.

### **3.3.2 Chunking**

Documents are split into smaller segments (approximately 400–600 characters) to improve retrieval accuracy using semantic chunking.

### **3.3.3 Embedding Generation**

Each document chunk is converted into vector embeddings using a pre-trained model (e.g., SentenceTransformers).

### **3.3.4 Vector Storage**

Embeddings are stored in a vector database (FAISS) for efficient similarity search.

### **3.3.5 Retrieval**

Given a user query, the system retrieves the top-k most relevant document chunks based on semantic similarity.

### **3.3.6 Response Generation**

The retrieved context is passed to a Large Language Model (LLM), which generates a response using only the provided information. Prompt engineering will determine the system prompt upon which the agent behaves in accordance to.

### **3.3.7 Depth Control**

The number of retrieved documents is adjusted based on the user-selected depth:

* Quick Mode: Top 3 documents  
* Deep Mode: Top 7 documents

# **4\.  Functional Requirements**

The system shall:

* Accept user queries  
* Retrieve relevant documents  
* Generate grounded responses  
* Display supporting sources  
* Maintain conversation context

