Video Demo Link: https://youtu.be/LN3fzlu4HxI


Slide Deck Link: https://drive.google.com/file/d/1W8lKjVMUin_-UBZnLszV9LQTx8Jz1R9G/view?usp=sharing

Live prototype: https://hackthon-monash-averis-project-velox.streamlit.app 


# HOW TO SETUP
# 1. Run these commands after cloning:
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

# Written Response
**Problem-solution alignment**

The implementation of various different modules in Velox aims to solve the core issues that are faced in the original problem statement. According to the aforementioned problem statement, the root causes of the issues (time consumption, manual comparison, same information looking different) stem from human error. In order to minimize and potentially fully mitigate these issues, our solution proposes the usage of AI models in order to sort, process, and escalate the emails whenever necessary.

To elaborate on how our system aims to solve these issues, we'll be breaking down our system into 4 main modules, each designed to handle a specific issue.

1. Classification: Emails will be fed into AI models, allowing them to be read and processed by said models. The AI will then give each email a specific classification. As this process is done automatically, failure rate due to human error is almost nonexistent, ensuring accuracy. 

2. Extraction: Emails that are marked as requiring comparison requests will only proceed to this section. Emails that reach this module are then classified into 2 categories, text and image. For a text readable file, python libraries will be used in conjunction with AI models in order to properly extract, normalize and sanitize the data. The same applies for read-only image files, where the AI model that will be used will have to be a vision capable model. 

3. Comparison: After the data is extracted, the information will be sent to this module. This module automatically compares the shipping instruction (SI) and BL (bill of lading) and ensures that the data for both fields completely match. If the fields do not match, the error in the email will be surfaced. This will be done with the assistance of code alongside AI models, which will significantly reduce the human error rate. 

4. Escalation: Lastly, emails that reach this stage are emails that require human intervention and review. If a file happens to be unreadable, corrupted, or contain any sort of major error that renders it unextractable, it will be escalated to a human for review. This ensures that time is not wasted on meaningless emails, and only the most important errors get brought to the attention of a human.

**AI and cloud infrastructure integration**

Velox uses multiple AI models that are hosted through the cloud in order to ensure scalability and minimal processing power. These AI models are used through the usage of multiple API keys that cycle through each other in order to ensure that the per minute limit is not hit before the emails finish the entire process cycle. 

**User feedback/testing**

As of right now, we have achieved an 82% success rate in processing all of the emails from the test case. Further review showed that a good percentage of the failed emails were not due to an error in the same, but due to the occasional rate limit in one of the API keys. Ideally, we would not have to rely on the free tier for these API keys, allowing us to use larger and more powerful models with better limits, which should further push the success rate in the processing cycle. 

**Coding challenges**

A few issues were encountered during the development of this, but the most prevalent issue by far was the limits placed upon us by the free tier for the API keys. We found a way around this by creating multiple accounts, each having their own API key. Then, we'd cycle through each API key, which would allow us to split the load to multiple keys which should give us enough leeway to properly process all of the emails in the given test case. 

Another issue that was faced was that during the earlier stages of testing, validation was too strict. This caused the system to reject perfectly good documents because of a minor error due to faulty OCR scanning. In order to solve this issue, we loosened up the requirements in which a field would be deemed rejected. A document will only be rejected if there are explicit placeholders such as "TBA" or null values. By doing this, the success rate will be improved and more emails will be able to be marked correctly.

**Success metrics** 

Our metrics of success are the percentage of emails that get marked correctly. These emails are tested against the ground truth and then calculated based off the formula: (number of successfully processed emails) / (number of total emails).

**Scalability plans**

Velox is easily scalable in various ways. Mainly, stronger tiers for AI and more accessibility options for different platforms and devices. As of right now, Velox is extremely limited in the sense that the limits of free tier API keys are extremely small and limiting. If they were to be improved upon, we would have access to bigger limits, more models and overall faster processing speed.

Ideally, this system would run on the backend of a cloud server. As such, we believe that we could further expand this program by allowing it to be accessed from multiple devices, not just on a computer. This way, an executive or an admin will be able to check the system for any processed emails from anywhere and any time, allowing productivity and efficiency to be increased.


