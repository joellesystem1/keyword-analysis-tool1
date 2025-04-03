# Keyword Analysis Tool - Super Easy Setup! 🚀

Hi! This tool will help you analyze your keyword data. Let's set it up together! 

## Step 1: Install Python (Skip if you already have it!)
1. Click this link: https://www.python.org/downloads/
2. Click the big yellow "Download Python" button
3. Once downloaded, open the installer
4. **IMPORTANT**: Check the box that says "Add Python to PATH" ✅
5. Click "Install Now"

## Step 2: Get Ready (One-time setup)
1. Create a new folder on your computer called "Keyword Tool"
2. Put these three files in that folder:
   - keyword_analyzer.py
   - requirements.txt
   - README.md (this file!)

## Step 3: Set Up Your Tool (One-time setup)
1. Open Terminal (Mac) or Command Prompt (Windows):
   - **Mac**: Press Command (⌘) + Space, type "terminal", press Enter
   - **Windows**: Press Windows + R, type "cmd", press Enter

2. Copy and paste these commands one at a time (press Enter after each):
   ```bash
   # First, go to your folder (change this to your folder's location!)
   cd "path/to/your/Keyword Tool"

   # Create a special environment (Windows)
   python -m venv .venv
   .venv\Scripts\activate

   # OR for Mac:
   python -m venv .venv
   source .venv/bin/activate

   # Install the required stuff
   pip install -r requirements.txt
   ```

## Step 4: Start Using the Tool! 🎉
Every time you want to use the tool:

1. Open Terminal/Command Prompt (like in Step 3)
2. Go to your folder:
   ```bash
   cd "path/to/your/Keyword Tool"
   ```
3. Activate the environment:
   - **Windows**: `.venv\Scripts\activate`
   - **Mac**: `source .venv/bin/activate`
4. Start the tool:
   ```bash
   streamlit run keyword_analyzer.py
   ```
5. The tool will open in your web browser automatically! 🌟

## Using Your New Tool
1. Click "Browse files" to upload your Excel file
2. Use the checkboxes at the top to:
   - Select which partners to analyze
   - Choose your dates
   - Set minimum clicks
3. Look at your data in different ways:
   - See who's performing best
   - Track trends over time
   - View keyword categories
4. Download any results you want to save!

## Need Help? 🆘
- If you see any error messages, take a screenshot
- Contact the person who shared this tool with you
- They'll help you get it working! 😊

## Pro Tips! 💡
- Keep your Excel file in the same folder as the tool
- Make sure your Excel file has these columns:
  - PARTNER_NAME
  - QUERY
  - NET_REVENUE
  - RPC
  - CLICKS
- Don't close the Terminal/Command Prompt while using the tool 