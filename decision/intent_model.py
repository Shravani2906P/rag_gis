from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

data=[
("hi","chitchat"),
("hello","chitchat"),
("what is anicut","info"),
("tell me about talab","info"),
("suggest structure","recommendation"),
("can i build","recommendation"),
("area 2 depth 1","recommendation")
]

texts=[x[0]for x in data]
labels=[x[1]for x in data]

vectorizer=TfidfVectorizer()
X=vectorizer.fit_transform(texts)

model=LogisticRegression()
model.fit(X,labels)

def predict_intent(q):
    X=vectorizer.transform([q])
    probs=model.predict_proba(X)[0]
    if max(probs)<0.5:
        return "unknown"
    return model.classes_[probs.argmax()]