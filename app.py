from flask import Flask, render_template, request, jsonify
import pandas as pd
import requests
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import joblib

app = Flask(__name__)

# Load your already created embeddings file
df = joblib.load("embedding.joblib")

# -------- Ollama Embedding --------
def create_embedding(text_list):
    r = requests.post("http://localhost:11434/api/embed", json={
        "model": "bge-m3",
        "input": text_list
    })
    return r.json()["embeddings"]

# -------- Ollama LLM --------
def inference(prompt):
    r = requests.post("http://localhost:11434/api/generate", json={
        "model": "llama3.2:3b",
        "prompt": prompt,
        "stream": False
    })
    return r.json()["response"]

# -------- RAG Pipeline --------
def rag_answer(user_question):
    question_embedding = create_embedding([user_question])[0]

    similarity = cosine_similarity(
        np.vstack(df["embedding"].values),
        [question_embedding]
    ).flatten()

    top_k = 5
    max_index = similarity.argsort()[::-1][:top_k]
    new_df = df.loc[max_index]

    prompt = f'''
I am teaching web development in my Sigma Web Development Course. Here are video subtitle chunks containing video title , video number , start time in seconds , end time in seconds , the text at that time : 

{new_df[['title','number','text','start','end']].to_json(orient='records')}
------------------------------------
"{user_question}"

User asked this question related to the video chunks, you have to answer in a human way and guide the user to go to that particular video and timestamp.
If user asks unrelated question, tell him that you can only answer questions related to the course.
'''

    answer = inference(prompt)
    return answer

# -------- Flask Routes --------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    answer = rag_answer(question)

    return jsonify({"answer": answer})

if __name__ == "__main__":
    app.run(debug=True)
