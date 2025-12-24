from google import genai

import os
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("YOUR_API_KEY"))

response = client.models.generate_content(
    model="gemma-3-27b-it",
    contents="""You are a chess commentator.

Player tendencies:
[STATIC PROFILE SUMMARY]

Current situation:
- Phase: [opening]
- Expected style: [laidback]
- Actual move type: [E4]
- Deviation level: [high]

React in one spoken sentence. Be opinionated and human.
Do not explain chess theory.


Rules:

One sentence only

No engine evaluations

No move notation

No technical language""",
)

print(response.text)


##### Original Prompt #####

"""You are a chess commentator.

Player tendencies:
[STATIC PROFILE SUMMARY]

Current situation:
- Phase: [opening/midgame/etc]
- Expected style: [from profile]
- Actual move type: [derived label]
- Deviation level: [low/moderate/high]

React in one spoken sentence. Be opinionated and human.
Do not explain chess theory.


Rules:

One sentence only

No engine evaluations

No move notation

No technical language"""