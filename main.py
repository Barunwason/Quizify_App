from langchain_groq import ChatGroq
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from typing import TypedDict
from dotenv import load_dotenv
import json
load_dotenv()

with open('/Users/barunwason/Langchain/quiz/schema.json','r') as file:
    quiz_schema=json.load(file)
    
model=ChatGroq(model="llama-3.3-70b-versatile")
structured_model=model.with_structured_output(quiz_schema)
parser=JsonOutputParser()
template1=PromptTemplate(
    template="give questions on {topic}",
    input_variables=['topic']
)
chain=template1 | structured_model 
def generate_quiz(topic:str):
    result=chain.invoke({'topic':topic})
    with open('/Users/barunwason/Langchain/quiz/static/questions.json','w') as file:
        quiz_schema=json.dump(result,file)

generate_quiz('mobile')

