"""Attacker models (plan M2/M5). RF is primary; logreg + gradient boosting are the second attackers."""
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def make_model(name, seed=0, trees=300):
    if name == "rf": return RandomForestClassifier(trees, random_state=seed, class_weight="balanced")
    if name == "logreg": return make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000, random_state=seed))
    if name == "gboost": return GradientBoostingClassifier(random_state=seed)
    raise ValueError(name)

def fit_predict(name, Xtr, ytr, Xte, seed=0, trees=300):
    m = make_model(name, seed, trees).fit(Xtr, ytr)
    return m, m.predict(Xte), m.predict_proba(Xte)
