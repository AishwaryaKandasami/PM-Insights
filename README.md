# PM Insights Engine 🚀

An AI-powered feedback analysis engine that transforms raw App Store/Play Store reviews into actionable product insights. Designed specifically for Product Managers, this tool automates the entire feedback loop—from initial scraping to final roadmap prioritization in Notion.

## 🏗️ Architecture: The 5 Phases

1.  **Phase 1: Multi-Source Scraping & Normalization**
    *   Scrapes thousands of reviews from the Google Play Store and Apple App Store.
    *   Normalizes raw data, handles deduplication, and masks PII (Personally Identifiable Information).
2.  **Phase 2: LLM-Powered Atomic Extraction**
    *   Uses **Gemini Flash** & **Groq** to extract "atoms" of information (Bugs, Feature Requests, User Sentiment).
    *   Classifies and routes feedback based on product area and urgency.
3.  **Phase 3: Adaptive Clustering**
    *   Clusters similar feedback using `scikit-learn` and AI-driven label adjudication.
    *   Calculates frequency, signal confidence, and severity for every cluster.
4.  **Phase 4: Artifact Assembly**
    *   Generates four key PM artifacts: a **Bug Triage Matrix**, **Feature Request Backlog**, **RICE Prioritization Table**, and a high-level **Executive Summary**.
5.  **Phase 5: Automated Notion Delivery**
    *   Publishes all artifacts directly into a Notion workspace via the official Notion SDK.
    *   Creates a structured "Insights Page" for every run, complete with relational databases for tracking progress.

## 🛠️ Tech Stack

*   **Logic**: Python 3.10+
*   **Intelligence**: Gemini 1.5 Pro/Flash, Groq (Llama 3)
*   **Database**: SQLite (Gold/Silver layers)
*   **Integrations**: Notion SDK (Phase 5 Delivery)
*   **Processing**: Scikit-Learn (Clustering), Pandas (Normalization)

## 🚀 Getting Started

1.  **Setup Credentials**: Add your `GEMINI_API_KEY`, `NOTION_TOKEN`, and `NOTION_PAGE_ID` to the `.env` file.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the Engine**:
    ```bash
    python run_phase4.py --run_id <YOUR_RUN_ID>
    ```
    *This will trigger the full analysis and automatically push the results to your Notion workspace.*

---
*Built with ❤️ for Product Managers who want to listen better to their users.*
