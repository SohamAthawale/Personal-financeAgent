from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

def build_category_model():
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1,2),
            min_df=2,
            max_features=5000
        )),
        ("clf", LogisticRegression(max_iter=1000))
    ])
