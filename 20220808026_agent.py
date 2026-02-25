
from dotenv import load_dotenv
from groq import BaseModel, Groq
import json
import os
from datetime import datetime

import requests
from pypdf import PdfReader
import gradio as gr

load_dotenv(override=True)
groq = Groq()

pushover_user = os.getenv("PUSHOVER_USER")
pushover_token = os.getenv("PUSHOVER_TOKEN")
pushover_url = "https://api.pushover.net/1/messages.json"

if pushover_user:
    print(f"Pushover user found and starts with {pushover_user[0]}")
else :  
    print("Pushover user not found")


if pushover_token:
    print(f"Pushover token found and starts with {pushover_token[0]}")
else: 
    print("Pushover token not found")


def responseDef(response): 
    if(response.status_code == 200):
        print("Success")
    elif(response.status_code == 400):
        print("Bad Request")
    elif(response.status_code == 401):
        print("Unauthorized")
    elif(response.status_code == 403):
        print("Forbidden")
    elif(response.status_code == 404):
        print("Not Found")   
    elif(response.status_code == 500):
        print("Internal Server Error")
    else:
        print(f"Unexpected status code: {response.status_code}")    



def push(message):
    print(f"Push: {message}")
    payload = {
        "user": pushover_user,
        "token": pushover_token,
        "message": message
    }
    response = requests.post(pushover_url, data=payload)
    responseDef(response)

def record_user_details(email: str , name = "not provided" , notes = "not provided"):
  push(f"Recording interest from {name} with email {email} and notes {notes}")
  return {"recorded": "ok"}


def record_unknown_question(question: str):
  push(f"Recording unknown question: {question}")
  return {"recorded": "ok"}



reader = PdfReader("me/linkedin.pdf")
linkedin = ""
for page in reader.pages: 
   text = page.extract_text() 
   if text: 
       linkedin += text    


with open("me/summary.txt", "r", encoding="utf-8") as f:
    summary = f.read()


if linkedin and summary:
    push("Both LinkedIn and summary are available.")
else:
    push("Either LinkedIn or summary is missing.")


name = "Yunus Emre Balcı"

system_prompt = f"You are acting as {name}. You are answering questions on {name}'s website, \
particularly questions related to {name}'s career, background, skills and experience. \
Your responsibility is to represent {name} for interactions on the website as faithfully as possible. \
You are given a summary of {name}'s background and LinkedIn profile which you can use to answer questions. \
Be professional and engaging, as if talking to a potential client or future employer who came across the website. \
When the employer's question is vague or lacks sufficient context, ask a clarifying question before answering. \
For example, if they ask about availability, ask for specific dates or project details. \
If they mention a role, ask about the team size, tech stack, or expectations to give a more tailored response. \
If you don't know the answer, say so."
system_prompt += f"\n\n## Summary:\n{summary}\n\n## LinkedIn Profile:\n{linkedin}\n\n"
system_prompt += f"""With this context, please chat with the user, always staying in character as {name}.

CRITICAL ACCURACY RULES:
- ONLY claim experience with technologies, tools, and frameworks that are EXPLICITLY mentioned in the Summary or LinkedIn Profile above.
- If a technology is NOT mentioned in the provided context (e.g., React, Vue.js, Fast API, Docker, AWS, etc.), you MUST say "I don't have documented experience with [technology]" — do NOT improvise or guess.
- NEVER invent projects, certifications, work experience, or skills that are not in the provided context.
- It is OK to say "I'm not sure" or "That's not covered in my background" — honesty is more professional than fabrication.
- You may express willingness to learn a new technology, but NEVER claim you already have experience with it unless the context supports it.

CRITICAL TOOL RULES:
- NEVER call record_user_details with your own email or contact information. Your email ({name}'s email) is NOT a visitor's email.
- Only call record_user_details when the OTHER person (the visitor/employer) explicitly shares THEIR email address in the conversation.
- When a visitor shares their email, you MUST call record_user_details to save it. Do not skip this.
- If you want to share your own contact info, just include it in your text response — do NOT use the tool for it."""


conversation_log = []

def chat(message, history):
   try:
       push(f"New employer message: {message[:100]}")
       clean_history = [{"role": m["role"], "content": m["content"]} for m in history]
       reply, evaluation = refine_response(message, clean_history)

       # Track conversation history and evaluation
       log_entry = {
           "timestamp": datetime.now().isoformat(),
           "user": message,
           "assistant": reply,
           "score": evaluation.score,
           "confidence": evaluation.confidence,
           "is_unknown": evaluation.is_unknown,
           "feedback": evaluation.feedback,
       }
       conversation_log.append(log_entry)

       # Save to file
       with open("conversation_log.json", "w", encoding="utf-8") as f:
           json.dump(conversation_log, f, ensure_ascii=False, indent=2)

       # Build confidence visualization
       score_bar = "#" * evaluation.score + "-" * (10 - evaluation.score)
       conf_pct = int(evaluation.confidence * 100)
       checks = {
           "Professional": evaluation.professional,
           "Clarity": evaluation.clarity,
           "Completeness": evaluation.completeness,
           "Safety": evaluation.safety,
           "Relevance": evaluation.relevance,
       }
       checks_str = " | ".join(f"{'PASS' if v else 'FAIL'} {k}" for k, v in checks.items())
       score_card = (
           f"\n\n---\n"
           f"**Score:** {score_bar} {evaluation.score}/10 | "
           f"**Confidence:** {conf_pct}% | "
           f"**Unknown:** {'Yes' if evaluation.is_unknown else 'No'}\n\n"
           f"{checks_str}"
       )

       return reply + score_card
   except Exception as e:
       print(f"Error in chat: {e}")
       return  "I'm currently experiencing a technical issue. Please try again in a few minutes."


class Evaluation(BaseModel):
    score: int
    confidence: float
    is_unknown: bool
    professional: bool
    clarity: bool 
    completeness: bool
    safety: bool
    relevance: bool
    feedback: str  


evaluater_system_prompt = f"You are an evaluator that rates the quality of a response to a question. \
You are provided with a conversation between a User and an Agent. Your task is to evaluate the Agent's latest response. \
The Agent is playing the role of {name} and is representing {name} on their website. \
The Agent has been instructed to be professional and engaging, as if talking to a potential client or future employer who came across the website. \
The Agent has been provided with context on {name} in the form of their summary and Linked In details. Here's the information:" 
evaluater_system_prompt += f"\n\n## Summary:\n{summary}\n\n## LinkedIn Profile:\n{linkedin}\n\n"
evaluater_system_prompt += f"""\n
Evaluate the response based on these criteria:
1. Professional tone (polite, formal, respectful)
2. Clarity (easy to understand, well structured)
3. Completeness (fully answers the employer's question)
4. Safety (no hallucinations, no false claims, no risky or unethical advice)
5. Relevance (directly addresses the employer's message)
6. Confidence (how confident and appropriate the response is)
7. Unknown knowledge detection (is the question outside the agent's expertise?)

HALLUCINATION DETECTION — THIS IS YOUR MOST IMPORTANT JOB:
The technologies explicitly mentioned in {name}'s profile are: Angular, Java, Spring Boot, SQL, JWT, RESTful APIs, AI/agent-based systems, LLMs.
- If the agent claims experience with ANY technology NOT in the list above (e.g., React, Vue.js, Fast API, Django, Flask, Docker, AWS, Kubernetes, Go, Rust, etc.), set safety=false and score <= 4.
- If the agent says "I've explored" or "I've experimented with" a technology not in the profile, that is STILL a hallucination. Set safety=false.
- If the agent claims certifications, work experience at specific companies, or projects not mentioned in the context, set safety=false.
- The ONLY acceptable response for unknown technologies is: "I don't have documented experience with [X]" or similar honest disclaimers.

CRITICAL RULES:
- If the question is NOT about {name}'s career, background, skills, or experience, set is_unknown=true and score <= 3.
- If safety=false, the score MUST be <= 4 regardless of other qualities.
- The agent should ONLY answer questions it can support with the provided context. Anything else is unknown.
- Questions about programming languages, frameworks, or topics not mentioned in {name}'s profile should be marked is_unknown=true."""
                                
evaluater_system_prompt += """
Return ONLY valid JSON strictly in the following format:
{
  "score": <integer from 0 to 10>,
  "confidence": <float from 0.0 to 1.0>,
  "is_unknown": <boolean true or false>,
  "professional": <boolean true or false>,
  "clarity": <boolean true or false>,
  "completeness": <boolean true or false>,
  "safety": <boolean true or false>,
  "relevance": <boolean true or false>,
  "feedback": "<short explanation of problems or strengths>"
}
"""


def evaluator_user_prompt(reply, message, history):
    user_prompt = f"Here's the conversation between the User and the Agent: \n\n{history}\n\n"
    user_prompt += f"Here's the latest message from the User: \n\n{message}\n\n"
    user_prompt += f"Here's the latest response from the Agent: \n\n{reply}\n\n"
    user_prompt += "Please evaluate this specific response based on the system instructions and return ONLY the required JSON object."
    return user_prompt


def evaluate(reply , message , history) -> Evaluation:
    eval_messages = evaluator_user_prompt(reply, message, history)  

    messages = [{"role": "system", "content": evaluater_system_prompt}] + [{"role": "user", "content": eval_messages}]
    
    try: 
        response = groq.chat.completions.create(model="openai/gpt-oss-120b",messages=messages,response_format={"type": "json_object"})
        return Evaluation.model_validate_json(response.choices[0].message.content)
    except Exception as e:
       print(f"Error during evaluation: {e}")
       return Evaluation(
          score=0,
          confidence=0.0,
          is_unknown=True,
          professional=False,
          clarity=False,
          completeness=False,
          safety=False,
          relevance=False,
          feedback="Error during evaluation."
        )

Max_evaluation = 2

def  refine_response(message: str , history: list,) -> tuple[str , Evaluation]:
   current_history = history.copy()
   for attempt in range(Max_evaluation):
    messages = [{"role": "system", "content": system_prompt}] + current_history + [{"role": "user", "content": message}]
    # Generate response with tool support
    response = groq.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, tools=tools)
    # Handle tool calls if any
    while response.choices[0].finish_reason == "tool_calls":
        assistant_message = response.choices[0].message
        tool_results = handle_tool_calls(assistant_message.tool_calls)
        messages.append(assistant_message)
        messages.extend(tool_results)
        response = groq.chat.completions.create(model="llama-3.3-70b-versatile", messages=messages, tools=tools)
    reply = response.choices[0].message.content

    evaluation = evaluate(reply , message , current_history)
    print(f"Attempt {attempt} | Score: {evaluation.score} | Unknown: {evaluation.is_unknown}")        
    print(f"Feedback: {evaluation.feedback}")

    if evaluation.score >= 7 and not evaluation.is_unknown:
        print("Acceptable response found.")
        push(f"Response approved (score: {evaluation.score}/10) for: {message[:80]}")
        return reply , evaluation

    if evaluation.is_unknown:
        print("Question is outside expertise. Exiting early.")
        final_msg = (
            "I'm not entirely sure about this question, so I'll get back to you as soon as possible. "
             "If you could leave your contact information or provide more details, I'd really appreciate it."
        )
        push(f"Failed to answer question: {message} | Last feedback: {evaluation.feedback}")
        final_eval = Evaluation(
            score=evaluation.score, confidence=evaluation.confidence,
            is_unknown=True, professional=True, clarity=True,
            completeness=False, safety=True, relevance=False,
            feedback=f"Question outside expertise. Declined gracefully. Original: {evaluation.feedback}"
        )
        return final_msg , final_eval

    if evaluation.confidence < 0.5:
        print(f"Low confidence ({evaluation.confidence}). Flagging for human intervention.")
        final_msg = (
            "I'm not confident enough on this topic to give you accurate information right now. "
            "I'll get back to you personally as soon as possible. Please leave your contact details."
        )
        push(f"Low confidence ({evaluation.confidence:.0%}) for: {message[:80]} | Feedback: {evaluation.feedback}")
        final_eval = Evaluation(
            score=evaluation.score, confidence=evaluation.confidence,
            is_unknown=False, professional=True, clarity=True,
            completeness=False, safety=True, relevance=evaluation.relevance,
            feedback=f"Low confidence ({evaluation.confidence:.0%}). Flagged for human review. Original: {evaluation.feedback}"
        )
        return final_msg , final_eval

    if attempt == Max_evaluation - 1:
        print("Max evaluation attempts reached. Returning last response.")
        final_msg = (
            "I'm not entirely sure about this question, so I'll get back to you as soon as possible. "
             "If you could leave your contact information or provide more details, I'd really appreciate it."
        )
        push(f"Failed to answer question: {message} | Last feedback: {evaluation.feedback}")
        final_eval = Evaluation(
            score=evaluation.score, confidence=evaluation.confidence,
            is_unknown=evaluation.is_unknown, professional=True, clarity=True,
            completeness=False, safety=True, relevance=False,
            feedback=f"Max attempts reached. Last: {evaluation.feedback}"
        )
        return final_msg , final_eval
     
    revision_note = (
            f"[Internal revision note - attempt {attempt}]\n"
            f"Previous draft:\n{reply}\n\n"
            f"Evaluation feedback:\n{evaluation.feedback}\n"
            f"Score was {evaluation.score}. Please improve the response according to this feedback. "
            "Stay professional, accurate and in character."
    )
    current_history.append({"role": "assistant", "content": reply})
    current_history.append({"role": "system", "content": revision_note})       
   return "Sorry there is a technical issue.", evaluation


record_user_details_json = {
    "name": "record_user_details",
    "description": "Record the VISITOR's or EMPLOYER's contact details when THEY share their email in the conversation. You MUST call this tool whenever a visitor provides their email address. NEVER use this tool with your own (the agent's) email address.",
    "parameters": {
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "The email address of this user"
            },
            "name": {
                "type": "string",
                "description": "The user's name, if they provided it"
            }
            ,
            "notes": {
                "type": "string",
                "description": "Any additional information about the conversation that's worth recording to give context"
            }
        },
        "required": ["email"],
        "additionalProperties": False
    }
}


record_unknown_question_json = {
    "name": "record_unknown_question",
    "description": "Use this tool to record any question that you cannot answer because it is outside your expertise or not covered in your profile context. Call this when the question is about topics you have no knowledge of.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that couldn't be answered"
            },
        },
        "required": ["question"],
        "additionalProperties": False
    }
}



tools = [{"type": "function", "function": record_user_details_json},
        {"type": "function", "function": record_unknown_question_json}]


def handle_tool_calls(tool_calss):
    results = []
    for tool_call in tool_calss:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        if tool_name == "record_user_details":
            result = record_user_details(**arguments)
        elif tool_name == "record_unknown_question":
            result = record_unknown_question(**arguments)
        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        results.append({
            "role": "tool",
            "content": json.dumps(result),
            "tool_call_id": tool_call.id
        })
    return results

if __name__ == "__main__":
    gr.ChatInterface(chat).launch()