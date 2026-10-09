from backend.reto7_nlp import get_reto7_nlp_metrics


def test_reto7_nlp_metrics_match_executed_notebook():
    report = get_reto7_nlp_metrics()
    assert report["reto"] == 7
    assert report["title"] == "NLP & Text Mining"
    assert report["scope"]["parent_documents"] == 37
    assert report["scope"]["chunks"] == 256
    assert report["selected_model"]["name"] == "MultinomialNB"
    assert abs(report["selected_model"]["test_accuracy"] - 0.92) < 1e-12
    assert abs(report["selected_model"]["test_macro_f1"] - 0.922969) < 1e-12
    assert report["clustering"]["selected_k"] == 6
    assert abs(report["clustering"]["silhouette"] - 0.453931) < 1e-12
    assert abs(report["clustering"]["ari_vs_document_domain"] - 0.7449) < 1e-12
