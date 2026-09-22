Video Demo Link:


Slide Deck Link: https://drive.google.com/file/d/1W8lKjVMUin_-UBZnLszV9LQTx8Jz1R9G/view?usp=sharing

Live prototype: https://hackthon-monash-averis-project-velox.streamlit.app 


# HOW TO SETUP
# 1. Run these commands:
pip install --upgrade pip
pip install -r requirements.txt

# 2. Create a .env file and paste these in:
GCP_API_KEY=your api key

GROQ_API_KEY_1= your api key

GROQ_API_KEY_2= your api key

GROQ_API_KEY_3= your api key

GROQ_API_KEY = your api key


GROQ_API_KEY_B=your api key
GROQ_API_KEY_1B=your api key
GROQ_API_KEY_2B=your api key


# 3. Run the code
To scan all the inbox emails and run the classifier, extractor and comparator module run this in the terminal:
python pipeline.py

# 4.To see the User Interface you can either:
Run this in the terminal(localhost, uses local submission.json result):
streamlit run app.py

OR

Use the live prototype link(Cloud hosted, uses present submission.json result)
https://hackthon-monash-averis-project-velox.streamlit.app  


